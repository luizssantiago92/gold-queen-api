"""Gold Queen API — FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.security_headers import SecurityHeadersMiddleware
from app.routers import (
    advisor_router,
    auth_router,
    chat_router,
    connections_router,
    dashboard_router,
)
from app.services.ai import get_ai_engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # create_all is synchronous SQL. The lifespan itself is async, so the
    # call has to leave the loop or startup stalls every other task.
    await run_in_threadpool(init_db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "RESTful API for Open Finance data aggregation, automated transaction "
            "categorization, and a medieval-themed financial AI advisor."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=settings.allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Added after CORS so this middleware sees the response last and only
    # appends headers. It does not replace the response or the allow-origin.
    app.add_middleware(SecurityHeadersMiddleware)

    register_exception_handlers(app)

    for router in (
        auth_router,
        connections_router,
        dashboard_router,
        advisor_router,
        chat_router,
    ):
        app.include_router(router)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs", status_code=307)

    @app.get("/health", tags=["health"])
    def health(
        session: SessionDep,
        response: Response,
        db: bool = False,
        deep: bool = False,
    ) -> dict[str, object]:
        # Local flags only. Render polls this path, so it must not call Gemini
        # or expose the deployment environment. gold-queen-web does not read it.
        body: dict[str, object] = {
            "status": "ok",
            "pluggy_live": settings.pluggy_enabled,
            "ai_live": settings.gemini_enabled,
        }
        # Opt-in provider probe. `?deep=1` is the only path that calls Gemini.
        if deep:
            ai_configured = settings.gemini_enabled
            ai_reachable = (
                get_ai_engine().provider_healthy() if ai_configured else False
            )
            body["ai_provider"] = (
                "ok" if ai_reachable else ("degraded" if ai_configured else "offline")
            )
        # Opt-in so Render's frequent health checks stay DB-free. The keep-alive
        # workflow sends ?db=1 so the free Supabase project sees real activity.
        if db:
            try:
                session.execute(text("SELECT 1"))
                body["database"] = "ok"
            except SQLAlchemyError:
                body["status"] = "degraded"
                body["database"] = "unreachable"
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return body

    return app


app = create_app()

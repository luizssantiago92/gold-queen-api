"""Gold Queen API — FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.api.deps import SessionDep
from app.services.ai import get_ai_engine
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.routers import (
    advisor_router,
    auth_router,
    chat_router,
    connections_router,
    dashboard_router,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
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

    register_exception_handlers(app)

    for router in (
        auth_router,
        connections_router,
        dashboard_router,
        advisor_router,
        chat_router,
    ):
        app.include_router(router)

    @app.get("/health", tags=["health"])
    def health(
        session: SessionDep, response: Response, db: bool = False
    ) -> dict[str, object]:
        ai_engine = get_ai_engine()
        ai_configured = settings.gemini_enabled
        ai_reachable = ai_engine.provider_healthy() if ai_configured else False
        body: dict[str, object] = {
            "status": "ok",
            "environment": settings.environment,
            "pluggy_live": settings.pluggy_enabled,
            "ai_live": ai_configured,
            "ai_provider": "ok" if ai_reachable else ("degraded" if ai_configured else "offline"),
        }
        # Opt-in so Render's frequent health checks stay DB-free. The keep-alive
        # workflow sends ?db=1 so the free Supabase project sees real activity.
        if db:
            try:
                session.exec(text("SELECT 1"))
                body["database"] = "ok"
            except SQLAlchemyError:
                body["status"] = "degraded"
                body["database"] = "unreachable"
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return body

    return app


app = create_app()

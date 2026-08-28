"""Gold Queen API — FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
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
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "environment": settings.environment,
            "pluggy_live": settings.pluggy_enabled,
            "ai_live": settings.gemini_enabled,
        }

    return app


app = create_app()

"""Versioned API routers."""

from app.routers.advisor import router as advisor_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.connections import router as connections_router
from app.routers.dashboard import router as dashboard_router

__all__ = [
    "advisor_router",
    "auth_router",
    "chat_router",
    "connections_router",
    "dashboard_router",
]

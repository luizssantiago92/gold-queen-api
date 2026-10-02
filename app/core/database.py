"""Database engine and session management."""

from collections.abc import Generator

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = (
            {"check_same_thread": False}
            if settings.database_url.startswith("sqlite")
            else {}
        )
        _engine = create_engine(
            settings.database_url, echo=False, connect_args=connect_args
        )
    return _engine


def _enable_demo_quota_rls(engine: Engine) -> None:
    """Deny the Supabase Data API access to per-visitor quota rows.

    ``create_all`` adds ``demo_chat_usage`` on an existing database, and a new
    public table is exposed by PostgREST until row-level security is on. With
    no policy, the anon key cannot read client addresses. The table owner (the
    role this API uses) still bypasses RLS, matching the other tables.
    """
    if engine.dialect.name == "sqlite":
        return
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE demo_chat_usage ENABLE ROW LEVEL SECURITY")
        )


def init_db() -> None:
    """Create tables for models registered on the SQLModel metadata."""
    import app.models.entities  # noqa: F401  (register models before create_all)

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _enable_demo_quota_rls(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session

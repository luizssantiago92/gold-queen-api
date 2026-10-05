"""Database engine and session management."""

from collections.abc import Generator

from sqlalchemy import make_url
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

_engine: Engine | None = None


def schema_managed_by_models(database_url: str) -> bool:
    """Return whether startup may create tables from the SQLModel metadata.

    SQLite covers the local quick-start and the test suite. Postgres,
    including production, takes its schema only from Alembic.
    """
    return make_url(database_url).get_backend_name() == "sqlite"


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = (
            {"check_same_thread": False}
            if schema_managed_by_models(settings.database_url)
            else {}
        )
        _engine = create_engine(
            settings.database_url, echo=False, connect_args=connect_args
        )
    return _engine


def init_db() -> None:
    """Create SQLite tables from the registered SQLModel metadata.

    Postgres startup does not connect and does not emit DDL. Apply Alembic
    before serving a Postgres database.
    """
    import app.models.entities  # noqa: F401  (register models before create_all)

    if not schema_managed_by_models(get_settings().database_url):
        return
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session

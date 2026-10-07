"""Startup schema policy and Alembic drift against a fresh Postgres."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel

from app.core.config import get_settings
from app.core.database import get_engine, init_db, schema_managed_by_models
from tests.test_migration import _LoggingSnapshot

_ADMIN_URL = "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/postgres"
_CHECK_URL = (
    "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/gold_queen_schema_check"
)
_HEAD = "d4e7a2b81c05"
_TABLES = {
    "users",
    "bank_connections",
    "accounts",
    "transactions",
    "chat_cache",
    "chat_usage",
    "demo_chat_usage",
}
_TIMESTAMPTZ_COLUMNS = (
    ("users", "created_at"),
    ("bank_connections", "last_synced_at"),
    ("bank_connections", "created_at"),
    ("accounts", "updated_at"),
    ("transactions", "created_at"),
    ("chat_cache", "created_at"),
)


@pytest.mark.parametrize(
    ("url", "managed"),
    [
        ("sqlite:///./gold_queen.db", True),
        ("sqlite://", True),
        ("sqlite+pysqlite:///./gold_queen.db", True),
        ("postgresql+psycopg2://postgres@localhost/gold_queen", False),
        ("postgresql://postgres@localhost/gold_queen", False),
    ],
)
def test_schema_managed_by_models_follows_the_backend(url: str, managed: bool) -> None:
    assert schema_managed_by_models(url) is managed
    assert make_url(url).get_backend_name() == ("sqlite" if managed else "postgresql")


def test_sqlite_startup_creates_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'local.db'}"
    monkeypatch.setattr(get_settings(), "database_url", url)
    monkeypatch.setattr("app.core.database._engine", None)

    init_db()

    names = set(inspect(create_engine(url)).get_table_names())
    assert _TABLES <= names


def test_postgres_engine_skips_sqlite_connect_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_create_engine(*args: object, **kwargs: object) -> object:
        captured["args"] = args
        captured["connect_args"] = kwargs.get("connect_args")
        return object()

    monkeypatch.setattr(
        get_settings(),
        "database_url",
        "postgresql+psycopg2://postgres@localhost/gold_queen",
    )
    monkeypatch.setattr("app.core.database._engine", None)
    monkeypatch.setattr("app.core.database.create_engine", fake_create_engine)

    get_engine()

    assert captured["connect_args"] == {}


def test_postgres_startup_does_not_issue_schema_ddl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        get_settings(),
        "database_url",
        "postgresql+psycopg2://postgres:postgres@127.0.0.1:1/gold_queen",
    )
    monkeypatch.setattr("app.core.database._engine", None)

    def refuse_engine(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Postgres startup must not open a database engine")

    def refuse_create_all(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Postgres startup must not call create_all")

    monkeypatch.setattr("app.core.database.create_engine", refuse_engine)
    monkeypatch.setattr(SQLModel.metadata, "create_all", refuse_create_all)

    init_db()


def _postgres_accepts_connections() -> bool:
    try:
        engine = create_engine(_ADMIN_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


def _recreate_check_database() -> None:
    admin = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = 'gold_queen_schema_check' "
                "AND pid <> pg_backend_pid()"
            )
        )
        connection.execute(text("DROP DATABASE IF EXISTS gold_queen_schema_check"))
        connection.execute(text("CREATE DATABASE gold_queen_schema_check"))
    admin.dispose()


def test_alembic_head_matches_models_on_a_fresh_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not _postgres_accepts_connections():
        if os.environ.get("REQUIRE_SCHEMA_DRIFT_CHECK"):
            pytest.fail(
                "REQUIRE_SCHEMA_DRIFT_CHECK is set but Postgres is not reachable"
            )
        pytest.skip("Postgres is not running; CI does not provide a database service")

    _recreate_check_database()
    monkeypatch.setattr(get_settings(), "database_url", _CHECK_URL)
    monkeypatch.setattr("app.core.database._engine", None)
    config = Config("alembic.ini")
    try:
        with _LoggingSnapshot():
            command.upgrade(config, "head")
            command.check(config)
        engine = get_engine()
        with engine.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()
        assert revision == _HEAD
        inspector = inspect(engine)
        for table, column in _TIMESTAMPTZ_COLUMNS:
            stored = next(
                item for item in inspector.get_columns(table) if item["name"] == column
            )
            assert getattr(stored["type"], "timezone", False) is True
        chat_names = {
            item["name"] for item in inspector.get_unique_constraints("chat_usage")
        }
        demo_names = {
            item["name"] for item in inspector.get_unique_constraints("demo_chat_usage")
        }
        assert "uq_chat_usage_user_date" in chat_names
        assert "uq_demo_chat_usage_subject_date" in demo_names
        transaction_names = {
            item["name"] for item in inspector.get_unique_constraints("transactions")
        }
        assert "uq_transactions_account_pluggy_id" in transaction_names
    finally:
        get_engine().dispose()
        monkeypatch.setattr("app.core.database._engine", None)


def test_deployment_doc_names_alembic_as_the_only_schema_source() -> None:
    text_body = Path("docs/deployment.md").read_text()
    assert "Alembic" in text_body
    assert "alembic upgrade head" in text_body
    assert "alembic stamp c7a1b5e0d942" in text_body
    assert "d4e7a2b81c05" in text_body
    assert "uq_transactions_account_pluggy_id" in text_body
    assert "enable_row_level_security" in text_body
    for table in (
        "users",
        "bank_connections",
        "accounts",
        "transactions",
        "chat_cache",
        "chat_usage",
    ):
        assert table in text_body
    assert "create_all" in text_body
    assert "SQLite" in text_body


def test_readme_describes_alembic_for_postgres_and_sqlite_startup() -> None:
    text_body = Path("README.md").read_text()
    assert "Alembic" in text_body
    assert "SQLite" in text_body
    assert "alembic upgrade head" in text_body


def test_changelog_unreleased_records_the_schema_source() -> None:
    changelog = Path("CHANGELOG.md").read_text()
    unreleased, _released = changelog.split("## [1.0.0]", maxsplit=1)
    assert "Alembic" in unreleased
    assert "create_all" in unreleased
    assert 'version = "1.0.0"' in Path("pyproject.toml").read_text()

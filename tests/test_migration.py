"""Alembic revision for quota uniqueness and UTC timestamps."""

import logging
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings


class _LoggingSnapshot:
    """Undo Alembic fileConfig, which disables loggers it does not own."""

    def __enter__(self) -> "_LoggingSnapshot":
        root = logging.getLogger()
        manager = root.manager
        self._root_handlers = list(root.handlers)
        self._root_level = root.level
        names = list(manager.loggerDict)
        self._disabled = {name: logging.getLogger(name).disabled for name in names}
        self._levels = {name: logging.getLogger(name).level for name in names}
        self._handlers = {
            name: list(logging.getLogger(name).handlers) for name in names
        }
        return self

    def __exit__(self, *_exc: object) -> None:
        root = logging.getLogger()
        root.handlers[:] = self._root_handlers
        root.setLevel(self._root_level)
        for name, disabled in self._disabled.items():
            logger = logging.getLogger(name)
            logger.disabled = disabled
            logger.setLevel(self._levels[name])
            logger.handlers[:] = self._handlers[name]


def _load_revision():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "c7a1b5e0d942_quota_and_timestamptz.py"
    )
    spec = spec_from_file_location("quota_timestamptz", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_timestamptz_conversion_reads_existing_values_as_utc() -> None:
    revision = _load_revision()
    assert revision.TIMESTAMPTZ_USING == "{column} AT TIME ZONE 'UTC'"
    rendered = revision.TIMESTAMPTZ_USING.format(column="created_at")
    assert rendered == "created_at AT TIME ZONE 'UTC'"


def test_upgrade_dedupes_usage_rows_and_adds_the_constraint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "migrate.db"
    # Patch the live settings object. Clearing the cache would hand later
    # tests a different object from the one the app captured at import.
    monkeypatch.setattr(get_settings(), "database_url", f"sqlite:///{database}")
    monkeypatch.setattr("app.core.database._engine", None)
    config = Config("alembic.ini")
    with _LoggingSnapshot():
        command.upgrade(config, "a630d3c39926")

    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (email, display_name, password_hash, created_at) "
                "VALUES ('quota@goldqueen.dev', 'Quota', 'x', '2026-10-01 00:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO chat_usage (user_id, usage_date, request_count) VALUES "
                "(1, '2026-10-01', 2), (1, '2026-10-01', 3)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE demo_chat_usage ("
                "id INTEGER PRIMARY KEY, "
                "user_id INTEGER NOT NULL, "
                "subject_key VARCHAR NOT NULL, "
                "usage_date DATE NOT NULL, "
                "request_count INTEGER NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO demo_chat_usage "
                "(user_id, subject_key, usage_date, request_count) VALUES "
                "(1, '203.0.113.5', '2026-10-01', 1), "
                "(1, '203.0.113.5', '2026-10-01', 4)"
            )
        )

    with _LoggingSnapshot():
        command.upgrade(config, "head")

    with engine.connect() as connection:
        chat_rows = connection.execute(
            text("SELECT request_count FROM chat_usage ORDER BY id")
        ).fetchall()
        demo_rows = connection.execute(
            text("SELECT request_count FROM demo_chat_usage ORDER BY id")
        ).fetchall()
    assert chat_rows == [(5,)]
    assert demo_rows == [(5,)]

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO chat_usage (user_id, usage_date, request_count) "
                "VALUES (1, '2026-10-01', 1)"
            )
        )

    with _LoggingSnapshot():
        command.downgrade(config, "a630d3c39926")
        command.upgrade(config, "head")
    with engine.connect() as connection:
        again = connection.execute(
            text("SELECT request_count FROM chat_usage")
        ).fetchall()
    assert again == [(5,)]


def test_upgrade_dedupes_transactions_and_adds_the_pluggy_constraint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "transactions.db"
    monkeypatch.setattr(get_settings(), "database_url", f"sqlite:///{database}")
    monkeypatch.setattr("app.core.database._engine", None)
    config = Config("alembic.ini")
    with _LoggingSnapshot():
        command.upgrade(config, "c7a1b5e0d942")

    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, email, display_name, password_hash, created_at) "
                "VALUES (1, 'queen@goldqueen.dev', 'Queen', 'x', "
                "'2026-08-28 00:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO bank_connections "
                "(id, user_id, pluggy_item_id, institution_name, status, created_at) "
                "VALUES (1, 1, 'item-1', 'Pluggy Bank', 'UPDATED', "
                "'2026-08-28 00:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO accounts "
                "(id, connection_id, pluggy_account_id, name, account_type, balance, "
                "currency, updated_at) VALUES "
                "(1, 1, 'acc-1', 'Checking', 'BANK', 100, 'BRL', "
                "'2026-08-28 00:00:00'), "
                "(2, 1, 'acc-2', 'Savings', 'BANK', 50, 'BRL', '2026-08-28 00:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO transactions "
                "(id, account_id, pluggy_transaction_id, description, amount, "
                "transaction_date, category, is_guarded, created_at) VALUES "
                "(1, 1, 'tx-salary', 'SALARIO EMPRESA XYZ LTDA', 8500, "
                "'2026-08-01', 'Income', 1, '2026-08-28 00:00:00'), "
                "(2, 1, 'tx-salary', 'SALARIO EMPRESA XYZ LTDA', 8500, "
                "'2026-08-01', 'Income', 1, '2026-08-28 00:00:01'), "
                "(3, 1, 'tx-salary-b', 'SALARIO EMPRESA XYZ LTDA', 8500.00, "
                "'2026-08-01', 'Income', 0, '2026-08-28 00:00:02'), "
                "(4, 1, 'tx-netflix', 'NETFLIX.COM', -39.90, "
                "'2026-08-28', 'Entertainment', 1, '2026-08-28 00:00:03'), "
                "(5, 1, 'tx-netflix-b', 'NETFLIX.COM', -39.90, "
                "'2026-08-28', 'Entertainment', 1, '2026-08-28 00:00:04'), "
                "(6, 1, 'tx-spotify', 'SPOTIFY AB', -21.90, "
                "'2026-08-15', 'Entertainment', 1, '2026-08-28 00:00:05'), "
                "(7, 1, 'tx-fit', 'SMART FIT ACADEMIA', -99.90, "
                "'2026-08-10', 'Health', 1, '2026-08-28 00:00:06'), "
                "(8, 1, 'tx-fit', 'SMART FIT ACADEMIA', -10.00, "
                "'2026-08-11', 'Health', 1, '2026-08-28 00:00:07'), "
                "(9, 2, 'tx-salary', 'SALARIO EMPRESA XYZ LTDA', 8500, "
                "'2026-08-01', 'Income', 1, '2026-08-28 00:00:08'), "
                "(10, 1, 'tx-netflix-big', 'NETFLIX.COM', -55.00, "
                "'2026-08-28', 'Entertainment', 1, '2026-08-28 00:00:09')"
            )
        )

    with _LoggingSnapshot():
        command.upgrade(config, "head")

    with engine.connect() as connection:
        kept = connection.execute(
            text("SELECT id FROM transactions ORDER BY id")
        ).fetchall()
    assert [row[0] for row in kept] == [1, 4, 6, 7, 9, 10]

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO transactions "
                "(account_id, pluggy_transaction_id, description, amount, "
                "transaction_date, category, is_guarded, created_at) VALUES "
                "(1, 'tx-salary', 'SALARIO EMPRESA XYZ LTDA', 8500, "
                "'2026-08-01', 'Income', 0, '2026-08-28 00:00:10')"
            )
        )

    with _LoggingSnapshot():
        command.downgrade(config, "c7a1b5e0d942")

    with engine.begin() as connection:
        still_kept = connection.execute(
            text("SELECT id FROM transactions ORDER BY id")
        ).fetchall()
        connection.execute(
            text(
                "INSERT INTO transactions "
                "(account_id, pluggy_transaction_id, description, amount, "
                "transaction_date, category, is_guarded, created_at) VALUES "
                "(1, 'tx-salary', 'SALARIO EMPRESA XYZ LTDA', 9000, "
                "'2026-08-02', 'Income', 0, '2026-08-28 00:00:11')"
            )
        )
    assert [row[0] for row in still_kept] == [1, 4, 6, 7, 9, 10]

    with _LoggingSnapshot():
        command.upgrade(config, "head")

    with engine.connect() as connection:
        again = connection.execute(
            text(
                "SELECT id, amount FROM transactions "
                "WHERE account_id = 1 AND pluggy_transaction_id = 'tx-salary'"
            )
        ).fetchall()
    assert len(again) == 1
    assert again[0][0] == 1

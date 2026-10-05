"""Atomic daily quota consumption."""

import threading
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.models.entities import ChatUsage, User, require_id
from app.services.rate_limit import consume_request


def test_concurrent_consume_stops_at_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "chat_daily_limit", 5)
    engine = create_engine(
        f"sqlite:///{tmp_path / 'quota.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_size=10,
        max_overflow=0,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(
            email="quota@goldqueen.dev", display_name="Quota", password_hash="x"
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = require_id(user.id)

    barrier = threading.Barrier(8)
    outcomes: list[str] = []
    lock = threading.Lock()

    def _worker() -> None:
        with Session(engine) as session:
            barrier.wait()
            try:
                consume_request(session, user_id, "en")
                kind = "ok"
            except RateLimitError:
                kind = "limited"
            with lock:
                outcomes.append(kind)

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("ok") == 5
    assert outcomes.count("limited") == 3
    with Session(engine) as session:
        rows = session.exec(select(ChatUsage)).all()
        assert len(rows) == 1
        assert rows[0].request_count == 5

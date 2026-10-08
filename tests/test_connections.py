"""Open Finance connection tests (RF01, RF02)."""

import inspect
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.entities import (
    Account,
    BankConnection,
    Transaction,
    User,
    require_id,
)
from app.routers.connections import create_connect_token, sync_connection
from app.services import sync as sync_service
from app.services.ai import AIEngine

ITEM_ALPHA = "11111111-1111-4111-8111-111111111111"
ITEM_BETA = "33333333-3333-4333-8333-333333333333"
ITEM_OWNED = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
ITEM_SHARED = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
ITEM_SLOTS = (
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa0",
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2",
)
ITEM_FOURTH = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa4"


def test_connect_token_is_issued(auth_client: TestClient) -> None:
    response = auth_client.post("/v1/connections/connect")
    assert response.status_code == 200

    body = response.json()
    assert body["connect_token"]
    assert body["connections_limit"] == 3
    assert body["connections_used"] == 0


def test_sync_creates_connection_accounts_and_transactions(
    auth_client: TestClient,
) -> None:
    response = auth_client.post("/v1/connections/sync", json={"item_id": ITEM_ALPHA})
    assert response.status_code == 200

    body = response.json()
    assert body["accounts_synced"] >= 1
    assert body["transactions_synced"] >= 1
    assert body["transactions_categorized"] == body["transactions_synced"]
    assert body["connection"]["pluggy_item_id"] == ITEM_ALPHA
    assert body["connection"]["last_synced_at"] is not None


def test_sync_is_idempotent(auth_client: TestClient) -> None:
    auth_client.post("/v1/connections/sync", json={"item_id": ITEM_BETA})
    second = auth_client.post("/v1/connections/sync", json={"item_id": ITEM_BETA})

    assert second.status_code == 200
    assert second.json()["transactions_synced"] == 0


def test_free_plan_allows_only_three_connections(auth_client: TestClient) -> None:
    for item_id in ITEM_SLOTS:
        assert (
            auth_client.post(
                "/v1/connections/sync", json={"item_id": item_id}
            ).status_code
            == 200
        )

    blocked = auth_client.post("/v1/connections/sync", json={"item_id": ITEM_FOURTH})
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "connection_limit_reached"

    token_blocked = auth_client.post("/v1/connections/connect")
    assert token_blocked.status_code == 403


def test_deleting_a_connection_frees_a_slot_and_erases_its_data(
    auth_client: TestClient,
) -> None:
    for item_id in ITEM_SLOTS:
        auth_client.post("/v1/connections/sync", json={"item_id": item_id})

    assert auth_client.post("/v1/connections/connect").status_code == 403

    connection_id = auth_client.get("/v1/connections").json()[0]["id"]
    assert auth_client.delete(f"/v1/connections/{connection_id}").status_code == 204

    assert len(auth_client.get("/v1/connections").json()) == 2
    # The quota is a one-way door unless deleting actually releases the slot.
    assert auth_client.post("/v1/connections/connect").status_code == 200

    # Transactions from the removed bank must not linger in the treasury.
    remaining = auth_client.get("/v1/dashboard/transactions").json()
    assert remaining["total"] > 0
    assert (
        auth_client.post(
            "/v1/connections/sync", json={"item_id": ITEM_SLOTS[0]}
        ).json()["transactions_synced"]
        > 0
    )


def test_deleting_someone_elses_connection_is_rejected(client: TestClient) -> None:
    def register_and_login(email: str) -> str:
        client.post(
            "/v1/auth/register",
            json={"email": email, "display_name": "User", "password": "StrongPass123!"},
        )
        response = client.post(
            "/v1/auth/login", json={"email": email, "password": "StrongPass123!"}
        )
        return response.json()["access_token"]

    owner = register_and_login("owner@goldqueen.dev")
    intruder = register_and_login("intruder@goldqueen.dev")

    client.post(
        "/v1/connections/sync",
        json={"item_id": ITEM_OWNED},
        headers={"Authorization": f"Bearer {owner}"},
    )
    connection_id = client.get(
        "/v1/connections", headers={"Authorization": f"Bearer {owner}"}
    ).json()[0]["id"]

    response = client.delete(
        f"/v1/connections/{connection_id}",
        headers={"Authorization": f"Bearer {intruder}"},
    )
    assert response.status_code == 404

    still_there = client.get(
        "/v1/connections", headers={"Authorization": f"Bearer {owner}"}
    ).json()
    assert len(still_there) == 1


def test_connections_are_scoped_per_user(client: TestClient) -> None:
    def register_and_login(email: str) -> str:
        client.post(
            "/v1/auth/register",
            json={"email": email, "display_name": "User", "password": "StrongPass123!"},
        )
        response = client.post(
            "/v1/auth/login", json={"email": email, "password": "StrongPass123!"}
        )
        return response.json()["access_token"]

    first = register_and_login("first@goldqueen.dev")
    second = register_and_login("second@goldqueen.dev")

    client.post(
        "/v1/connections/sync",
        json={"item_id": ITEM_SHARED},
        headers={"Authorization": f"Bearer {first}"},
    )

    response = client.get(
        "/v1/connections", headers={"Authorization": f"Bearer {second}"}
    )
    assert response.json() == []


def _register_and_login(client: TestClient, email: str) -> str:
    client.post(
        "/v1/auth/register",
        json={"email": email, "display_name": "User", "password": "StrongPass123!"},
    )
    response = client.post(
        "/v1/auth/login", json={"email": email, "password": "StrongPass123!"}
    )
    return response.json()["access_token"]


def _enable_pluggy(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    """Point the live Pluggy client at ``handler`` for one test."""
    settings = get_settings()
    monkeypatch.setattr(settings, "pluggy_client_id", "id")
    monkeypatch.setattr(settings, "pluggy_client_secret", "secret")
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def patched(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched)


def test_syncing_another_users_item_is_not_found(client: TestClient) -> None:
    owner = _register_and_login(client, "owner-sync@goldqueen.dev")
    intruder = _register_and_login(client, "intruder-sync@goldqueen.dev")

    created = client.post(
        "/v1/connections/sync",
        json={"item_id": ITEM_OWNED},
        headers={"Authorization": f"Bearer {owner}"},
    )
    assert created.status_code == 200

    stolen = client.post(
        "/v1/connections/sync",
        json={"item_id": ITEM_OWNED},
        headers={"Authorization": f"Bearer {intruder}"},
    )
    assert stolen.status_code == 404
    assert stolen.json() == {
        "detail": "Bank connection not found.",
        "code": "not_found",
    }

    intruder_rows = client.get(
        "/v1/connections", headers={"Authorization": f"Bearer {intruder}"}
    ).json()
    owner_rows = client.get(
        "/v1/connections", headers={"Authorization": f"Bearer {owner}"}
    ).json()
    assert intruder_rows == []
    assert len(owner_rows) == 1
    assert owner_rows[0]["pluggy_item_id"] == ITEM_OWNED


def test_sync_rejects_a_non_uuid_item_id(auth_client: TestClient) -> None:
    response = auth_client.post("/v1/connections/sync", json={"item_id": "../x"})
    assert response.status_code == 422
    assert auth_client.get("/v1/connections").json() == []


def test_sync_rejects_a_pluggy_item_owned_by_someone_else(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "key"})
        seen.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "id": ITEM_ALPHA,
                "status": "UPDATED",
                "clientUserId": "not-this-user",
                "connector": {"name": "Pluggy Bank"},
            },
        )

    _enable_pluggy(monkeypatch, handler)
    response = auth_client.post("/v1/connections/sync", json={"item_id": ITEM_ALPHA})

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert not any(path.startswith("/accounts") for path in seen)
    assert auth_client.get("/v1/connections").json() == []


def test_sync_does_not_leak_pluggy_error_bodies(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "pluggy-secret-9f3a2c"
    upstream_body = (
        f'{{"message":"item lookup denied","apiKey":"{secret}",'
        f'"clientSecret":"super-secret-value"}}'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "server-api-key"})
        return httpx.Response(403, text=upstream_body)

    _enable_pluggy(monkeypatch, handler)

    with caplog.at_level(logging.WARNING, logger="app.services.pluggy"):
        response = auth_client.post(
            "/v1/connections/sync", json={"item_id": ITEM_ALPHA}
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Pluggy item fetch failed.",
        "code": "upstream_error",
    }
    assert secret not in response.text
    assert "super-secret-value" not in response.text
    assert upstream_body not in response.text
    assert secret not in caplog.text
    assert "super-secret-value" not in caplog.text
    assert "403" in caplog.text
    assert auth_client.get("/v1/connections").json() == []


def test_connection_handlers_are_not_coroutines() -> None:
    assert not inspect.iscoroutinefunction(create_connect_token)
    assert not inspect.iscoroutinefunction(sync_connection)
    assert not inspect.iscoroutinefunction(sync_service.sync_item)


def test_sync_does_not_block_the_event_loop(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A blocked categorize must not stop another request on the same loop."""
    entered = threading.Event()
    release = threading.Event()

    def blocking_categorize(
        self: AIEngine, transactions: list[tuple[str, str, object]]
    ) -> tuple[dict[str, str], bool]:
        del self
        entered.set()
        if not release.wait(timeout=3):
            raise AssertionError("categorize was not released")
        return {tx_id: "Food" for tx_id, _, _ in transactions}, True

    monkeypatch.setattr(AIEngine, "categorize", blocking_categorize)

    # Futures re-raise whatever the request raised, so the test does not
    # swallow exceptions. release runs on the way out so a timeout cannot
    # leave categorize waiting.
    with ThreadPoolExecutor(max_workers=2) as pool:
        sync_future = pool.submit(
            auth_client.post,
            "/v1/connections/sync",
            json={"item_id": ITEM_ALPHA},
        )
        try:
            assert entered.wait(timeout=3)
            started = time.perf_counter()
            root_future = pool.submit(auth_client.get, "/", follow_redirects=False)
            root = root_future.result(timeout=1)
            elapsed = time.perf_counter() - started
        finally:
            release.set()
        sync_response = sync_future.result(timeout=3)

    assert elapsed < 1
    assert root.status_code == 307
    assert sync_response.status_code == 200


ITEM_DUPES = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


def _pluggy_page(
    results: list[dict[str, object]], next_page: str | None
) -> httpx.Response:
    return httpx.Response(200, json={"results": results, "next": next_page})


def test_sync_collapses_a_repeated_pluggy_id_and_upserts_on_the_next_fetch(
    auth_client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = str(auth_client.get("/v1/auth/me").json()["id"])
    today = date.today().isoformat()
    pages = {"count": 0}
    salary = {
        "id": "tx-salary",
        "description": "SALARIO EMPRESA XYZ LTDA",
        "amount": 8500,
        "date": today,
    }
    netflix = {
        "id": "tx-netflix",
        "description": "NETFLIX.COM",
        "amount": -39.9,
        "date": today,
    }
    spotify = {
        "id": "tx-spotify",
        "description": "SPOTIFY AB",
        "amount": -21.9,
        "date": today,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "key"})
        if request.url.path.startswith("/items/"):
            return httpx.Response(
                200,
                json={
                    "id": ITEM_DUPES,
                    "status": "UPDATED",
                    "clientUserId": user_id,
                    "connector": {"name": "Pluggy Bank"},
                },
            )
        if request.url.path == "/accounts":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "acc-dupes",
                            "name": "Checking",
                            "balance": 1000,
                            "currencyCode": "BRL",
                            "type": "BANK",
                        }
                    ]
                },
            )
        pages["count"] += 1
        if pages["count"] == 1:
            return _pluggy_page(
                [salary, salary, netflix, netflix],
                "https://api.pluggy.ai/v2/transactions?accountId=acc-dupes&page=2",
            )
        return _pluggy_page([salary, spotify], None)

    _enable_pluggy(monkeypatch, handler)
    first = auth_client.post("/v1/connections/sync", json={"item_id": ITEM_DUPES})
    assert first.status_code == 200
    assert first.json()["transactions_synced"] == 3

    overview = auth_client.get("/v1/dashboard/overview").json()
    assert Decimal(str(overview["month_income"])) == Decimal("8500.00")
    assert Decimal(str(overview["month_expenses"])) == Decimal("61.80")
    assert len(session.exec(select(Transaction)).all()) == 3

    pages["count"] = 0
    salary["amount"] = 9000
    salary["description"] = "FOLHA EMPRESA XYZ LTDA"
    shifted = date.today()
    if shifted.day > 1:
        shifted = shifted.replace(day=shifted.day - 1)
    salary["date"] = shifted.isoformat()
    second = auth_client.post("/v1/connections/sync", json={"item_id": ITEM_DUPES})
    assert second.status_code == 200
    assert second.json()["transactions_synced"] == 0
    assert second.json()["transactions_categorized"] == 0

    rows = session.exec(
        select(Transaction).where(Transaction.pluggy_transaction_id == "tx-salary")
    ).all()
    assert len(rows) == 1
    assert rows[0].amount == Decimal("9000.00")
    assert rows[0].description == "FOLHA EMPRESA XYZ LTDA"
    assert rows[0].transaction_date == shifted
    assert rows[0].category == "Income"
    refreshed = auth_client.get("/v1/dashboard/overview").json()
    assert Decimal(str(refreshed["month_income"])) == Decimal("9000.00")


ITEM_MOVEMENT = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"


def _serve_movement_pages(
    monkeypatch: pytest.MonkeyPatch,
    auth_client: TestClient,
    pages: list[list[dict[str, object]]],
) -> dict[str, int]:
    """Answer Pluggy with one transaction page per sync, in order."""
    user_id = str(auth_client.get("/v1/auth/me").json()["id"])
    state = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "key"})
        if request.url.path.startswith("/items/"):
            return httpx.Response(
                200,
                json={
                    "id": ITEM_MOVEMENT,
                    "status": "UPDATED",
                    "clientUserId": user_id,
                    "connector": {"name": "Pluggy Bank"},
                },
            )
        if request.url.path == "/accounts":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "acc-movement",
                            "name": "Checking",
                            "balance": 1000,
                            "currencyCode": "BRL",
                            "type": "BANK",
                        }
                    ]
                },
            )
        index = min(state["count"], len(pages) - 1)
        state["count"] += 1
        return _pluggy_page(pages[index], None)

    _enable_pluggy(monkeypatch, handler)
    return state


def test_sync_collapses_four_fresh_salary_ids_in_one_fetch(
    auth_client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    today = date.today().isoformat()
    amounts = ("8500", "8500.00", "8500.004", "8500")
    salaries: list[dict[str, object]] = [
        {
            "id": f"tx-salary-{index}",
            "description": "SALARIO EMPRESA XYZ LTDA",
            "amount": amount,
            "date": today,
        }
        for index, amount in enumerate(amounts, start=1)
    ]
    _serve_movement_pages(monkeypatch, auth_client, [salaries])

    response = auth_client.post("/v1/connections/sync", json={"item_id": ITEM_MOVEMENT})
    assert response.status_code == 200
    assert response.json()["transactions_synced"] == 1

    rows = session.exec(select(Transaction)).all()
    assert len(rows) == 1
    assert rows[0].pluggy_transaction_id == "tx-salary-1"
    assert rows[0].amount == Decimal("8500")
    overview = auth_client.get("/v1/dashboard/overview").json()
    assert Decimal(str(overview["month_income"])) == Decimal("8500.00")


def test_sync_skips_a_stored_movement_when_pluggy_mints_a_new_id(
    auth_client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    today = date.today().isoformat()
    salary = {
        "description": "SALARIO EMPRESA XYZ LTDA",
        "date": today,
    }
    first_page: list[dict[str, object]] = [
        {"id": "tx-salary-a", "amount": "8500", **salary}
    ]
    second_page: list[dict[str, object]] = [
        {"id": "tx-salary-b", "amount": "8500.004", **salary},
        {"id": "tx-salary-other", "amount": "100.00", **salary},
        {
            "id": "tx-netflix",
            "description": "NETFLIX.COM",
            "amount": "-39.90",
            "date": today,
        },
    ]
    _serve_movement_pages(
        monkeypatch,
        auth_client,
        [first_page, second_page],
    )

    first = auth_client.post("/v1/connections/sync", json={"item_id": ITEM_MOVEMENT})
    assert first.status_code == 200
    assert first.json()["transactions_synced"] == 1

    second = auth_client.post("/v1/connections/sync", json={"item_id": ITEM_MOVEMENT})
    assert second.status_code == 200
    assert second.json()["transactions_synced"] == 2

    rows = session.exec(select(Transaction)).all()
    by_id = {row.pluggy_transaction_id: row for row in rows}
    assert set(by_id) == {"tx-salary-a", "tx-salary-other", "tx-netflix"}
    assert by_id["tx-salary-a"].amount == Decimal("8500")
    assert by_id["tx-salary-other"].amount == Decimal("100.00")
    overview = auth_client.get("/v1/dashboard/overview").json()
    assert Decimal(str(overview["month_income"])) == Decimal("8600.00")


def test_movement_key_comment_records_identical_purchases_collapse() -> None:
    source = Path("app/services/sync.py").read_text(encoding="utf-8")
    assert "collapse into one row" in source


def test_persist_new_transaction_updates_the_row_when_the_key_exists(
    session: Session,
) -> None:
    user = User(
        email="sync-race@goldqueen.dev",
        display_name="Sync",
        password_hash="x",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    connection = BankConnection(
        user_id=require_id(user.id),
        pluggy_item_id="item-race",
        institution_name="Pluggy Bank",
    )
    session.add(connection)
    session.commit()
    session.refresh(connection)
    account = Account(
        connection_id=require_id(connection.id),
        pluggy_account_id="acc-race",
        name="Checking",
        balance=Decimal("0"),
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    account_id = require_id(account.id)
    original = Transaction(
        account_id=account_id,
        pluggy_transaction_id="tx-salary",
        description="SALARIO EMPRESA XYZ LTDA",
        amount=Decimal("8500.00"),
        transaction_date=date(2026, 8, 1),
        category="Income",
        is_guarded=True,
    )
    session.add(original)
    session.commit()
    session.refresh(original)

    sync_service._persist_new_transaction(
        session,
        Transaction(
            account_id=account_id,
            pluggy_transaction_id="tx-salary",
            description="FOLHA EMPRESA XYZ LTDA",
            amount=Decimal("9000.00"),
            transaction_date=date(2026, 8, 2),
            category="Uncategorized",
            is_guarded=False,
        ),
    )
    session.commit()

    rows = session.exec(select(Transaction)).all()
    assert len(rows) == 1
    assert rows[0].id == original.id
    assert rows[0].amount == Decimal("9000.00")
    assert rows[0].description == "FOLHA EMPRESA XYZ LTDA"
    assert rows[0].transaction_date == date(2026, 8, 2)
    assert rows[0].category == "Income"
    assert rows[0].is_guarded is True

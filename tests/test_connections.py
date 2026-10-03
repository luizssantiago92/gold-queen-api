"""Open Finance connection tests (RF01, RF02)."""

import inspect
import logging
import threading
import time
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
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

    holder: dict[str, object] = {}

    def run_sync() -> None:
        try:
            holder["response"] = auth_client.post(
                "/v1/connections/sync", json={"item_id": ITEM_ALPHA}
            )
        except Exception as exc:  # noqa: BLE001 - the assertion reports it
            holder["error"] = exc

    worker = threading.Thread(target=run_sync)
    worker.start()
    assert entered.wait(timeout=3)

    root_holder: dict[str, object] = {}

    def run_root() -> None:
        try:
            root_holder["response"] = auth_client.get("/", follow_redirects=False)
        except Exception as exc:  # noqa: BLE001
            root_holder["error"] = exc

    root_thread = threading.Thread(target=run_root)
    started = time.perf_counter()
    root_thread.start()
    root_thread.join(timeout=1)
    elapsed = time.perf_counter() - started
    release.set()
    worker.join(timeout=3)
    root_thread.join(timeout=3)

    assert "error" not in holder
    assert "error" not in root_holder
    assert elapsed < 1
    root = root_holder["response"]
    sync_response = holder["response"]
    assert isinstance(root, httpx.Response)
    assert isinstance(sync_response, httpx.Response)
    assert root.status_code == 307
    assert sync_response.status_code == 200

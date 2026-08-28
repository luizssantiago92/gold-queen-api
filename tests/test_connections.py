"""Open Finance connection tests (RF01, RF02)."""

from fastapi.testclient import TestClient


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
    response = auth_client.post("/v1/connections/sync", json={"item_id": "item-alpha"})
    assert response.status_code == 200

    body = response.json()
    assert body["accounts_synced"] >= 1
    assert body["transactions_synced"] >= 1
    assert body["transactions_categorized"] == body["transactions_synced"]
    assert body["connection"]["last_synced_at"] is not None


def test_sync_is_idempotent(auth_client: TestClient) -> None:
    auth_client.post("/v1/connections/sync", json={"item_id": "item-beta"})
    second = auth_client.post("/v1/connections/sync", json={"item_id": "item-beta"})

    assert second.status_code == 200
    assert second.json()["transactions_synced"] == 0


def test_free_plan_allows_only_three_connections(auth_client: TestClient) -> None:
    for index in range(3):
        assert (
            auth_client.post(
                "/v1/connections/sync", json={"item_id": f"item-{index}"}
            ).status_code
            == 200
        )

    blocked = auth_client.post("/v1/connections/sync", json={"item_id": "item-fourth"})
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "connection_limit_reached"

    token_blocked = auth_client.post("/v1/connections/connect")
    assert token_blocked.status_code == 403


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
        json={"item_id": "shared-item"},
        headers={"Authorization": f"Bearer {first}"},
    )

    response = client.get(
        "/v1/connections", headers={"Authorization": f"Bearer {second}"}
    )
    assert response.json() == []

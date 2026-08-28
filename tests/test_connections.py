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


def test_deleting_a_connection_frees_a_slot_and_erases_its_data(
    auth_client: TestClient,
) -> None:
    for index in range(3):
        auth_client.post("/v1/connections/sync", json={"item_id": f"item-{index}"})

    assert auth_client.post("/v1/connections/connect").status_code == 403

    connection_id = auth_client.get("/v1/connections").json()[0]["id"]
    assert auth_client.delete(f"/v1/connections/{connection_id}").status_code == 204

    assert len(auth_client.get("/v1/connections").json()) == 2
    # The quota is a one-way door unless deleting actually releases the slot.
    assert auth_client.post("/v1/connections/connect").status_code == 200

    # Transactions from the removed bank must not linger in the treasury.
    remaining = auth_client.get("/v1/dashboard/transactions").json()
    assert remaining["total"] > 0
    assert auth_client.post(
        "/v1/connections/sync", json={"item_id": "item-0"}
    ).json()["transactions_synced"] > 0


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
        json={"item_id": "owned-item"},
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
        json={"item_id": "shared-item"},
        headers={"Authorization": f"Bearer {first}"},
    )

    response = client.get(
        "/v1/connections", headers={"Authorization": f"Bearer {second}"}
    )
    assert response.json() == []

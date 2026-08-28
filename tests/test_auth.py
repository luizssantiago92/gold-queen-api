"""Authentication flow tests."""

from fastapi.testclient import TestClient


def test_register_and_login(client: TestClient) -> None:
    register = client.post(
        "/v1/auth/register",
        json={
            "email": "new@goldqueen.dev",
            "display_name": "New Subject",
            "password": "StrongPass123!",
        },
    )
    assert register.status_code == 201
    assert register.json()["email"] == "new@goldqueen.dev"

    login = client.post(
        "/v1/auth/login",
        json={"email": "new@goldqueen.dev", "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_duplicate_email_is_rejected(client: TestClient) -> None:
    payload = {
        "email": "dup@goldqueen.dev",
        "display_name": "Duplicate",
        "password": "StrongPass123!",
    }
    assert client.post("/v1/auth/register", json=payload).status_code == 201
    assert client.post("/v1/auth/register", json=payload).status_code == 409


def test_login_with_wrong_password_fails(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "wrong@goldqueen.dev",
            "display_name": "Wrong Pass",
            "password": "StrongPass123!",
        },
    )
    response = client.post(
        "/v1/auth/login",
        json={"email": "wrong@goldqueen.dev", "password": "NotThePassword1!"},
    )
    assert response.status_code == 401


def test_protected_route_requires_token(client: TestClient) -> None:
    assert client.get("/v1/dashboard/overview").status_code == 401


def test_me_returns_current_user(auth_client: TestClient) -> None:
    response = auth_client.get("/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "knight@goldqueen.dev"

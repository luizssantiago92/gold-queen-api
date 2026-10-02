"""Authentication flow tests."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, LoginRateLimitError
from app.core.login_rate_limit import enforce_login_rate_limit, login_client_key
from app.core.security import create_access_token, decode_access_token


def _request(
    headers: list[tuple[bytes, bytes]] | None = None,
    host: str = "203.0.113.9",
) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/v1/auth/login",
            "raw_path": b"/v1/auth/login",
            "query_string": b"",
            "headers": headers or [],
            "client": (host, 123),
            "server": ("test", 80),
        }
    )


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


def test_register_is_rejected_when_signup_is_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "allow_registration", False)
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "closed@goldqueen.dev",
            "display_name": "Closed Gate",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "Registration is disabled.",
        "code": "registration_disabled",
    }


def test_login_still_works_when_registration_is_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "email": "already@goldqueen.dev",
        "display_name": "Already Inside",
        "password": "StrongPass123!",
    }
    assert client.post("/v1/auth/register", json=payload).status_code == 201

    monkeypatch.setattr(get_settings(), "allow_registration", False)
    login = client.post(
        "/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    blocked = client.post(
        "/v1/auth/register",
        json={
            "email": "late@goldqueen.dev",
            "display_name": "Too Late",
            "password": "StrongPass123!",
        },
    )
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "registration_disabled"


def test_protected_route_requires_token(client: TestClient) -> None:
    assert client.get("/v1/dashboard/overview").status_code == 401


def test_me_returns_current_user(auth_client: TestClient) -> None:
    response = auth_client.get("/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "knight@goldqueen.dev"


def test_access_token_round_trip() -> None:
    assert decode_access_token(create_access_token("42")) == "42"


def test_tampered_token_is_rejected() -> None:
    token = create_access_token("42")
    with pytest.raises(AuthenticationError):
        decode_access_token(token[:-2] + "aa")


def test_expired_token_is_rejected() -> None:
    settings = get_settings()
    token = jwt.encode(
        {"sub": "42", "exp": datetime.now(UTC) - timedelta(minutes=5)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_token_without_subject_is_rejected() -> None:
    settings = get_settings()
    token = jwt.encode(
        {"exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_login_rate_limit_blocks_repeated_attempts(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "login_rate_limit_max", 2)
    payload = {"email": "nobody@goldqueen.dev", "password": "NotThePassword1!"}

    assert client.post("/v1/auth/login", json=payload).status_code == 401
    assert client.post("/v1/auth/login", json=payload).status_code == 401
    blocked = client.post("/v1/auth/login", json=payload)

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "login_rate_limited"
    assert blocked.headers["retry-after"].isdigit()


def test_login_client_key_prefers_platform_headers() -> None:
    proxied = _request(
        headers=[
            (b"x-forwarded-for", b"203.0.113.5, 10.0.0.1"),
            (b"x-real-ip", b"203.0.113.5"),
        ],
        host="10.0.0.1",
    )
    assert login_client_key(proxied, trust_proxy_headers=True) == "203.0.113.5"

    forwarded = _request(
        headers=[(b"x-forwarded-for", b"203.0.113.8, 10.0.0.2")],
        host="10.0.0.1",
    )
    assert login_client_key(forwarded, trust_proxy_headers=True) == "203.0.113.8"
    assert login_client_key(forwarded, trust_proxy_headers=False) == "10.0.0.1"


def test_login_window_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "login_rate_limit_max", 1)
    monkeypatch.setattr(settings, "login_rate_limit_window_seconds", 10)
    request = _request()

    enforce_login_rate_limit(request, now=100.0)
    with pytest.raises(LoginRateLimitError):
        enforce_login_rate_limit(request, now=105.0)
    enforce_login_rate_limit(request, now=111.0)

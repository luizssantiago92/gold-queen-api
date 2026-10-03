"""Password hashing compatible with hashes passlib already stored."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password, verify_password

# Produced by passlib 1.7.4 CryptContext(schemes=["bcrypt"]) on bcrypt 4.0.1
# for the password "StrongPass123!". The prefix and 12-round cost are what
# production rows already store.
PASSLIB_BCRYPT_HASH = "$2b$12$i4JenkQrauMKUOM2hJ6iq.55osq9Ve5PPeneBbyChX4B7oAIUFEty"
KNOWN_PASSWORD = "StrongPass123!"


def test_passlib_bcrypt_hash_still_verifies() -> None:
    assert PASSLIB_BCRYPT_HASH.startswith("$2b$")
    assert verify_password(KNOWN_PASSWORD, PASSLIB_BCRYPT_HASH)
    assert not verify_password("NotThePassword1!", PASSLIB_BCRYPT_HASH)


def test_hash_password_emits_bcrypt_2b_prefix() -> None:
    hashed = hash_password(KNOWN_PASSWORD)
    assert hashed.startswith("$2b$")
    assert verify_password(KNOWN_PASSWORD, hashed)
    assert not verify_password("NotThePassword1!", hashed)


def test_verify_rejects_password_longer_than_72_bytes() -> None:
    assert verify_password("a" * 73, PASSLIB_BCRYPT_HASH) is False


def test_verify_rejects_a_hash_that_is_not_bcrypt_text() -> None:
    assert verify_password(KNOWN_PASSWORD, "not-a-bcrypt-hash") is False
    assert verify_password(KNOWN_PASSWORD, "não-é-ascii") is False


def test_hash_password_rejects_password_longer_than_72_bytes() -> None:
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("a" * 73)


def test_register_rejects_password_longer_than_72_bytes(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "long@goldqueen.dev",
            "display_name": "Long Password",
            "password": "a" * 73,
        },
    )
    assert response.status_code == 422

    # 20 emoji are 80 UTF-8 bytes and still under the 128-character cap.
    multibyte = client.post(
        "/v1/auth/register",
        json={
            "email": "emoji@goldqueen.dev",
            "display_name": "Emoji Password",
            "password": "🔐" * 20,
        },
    )
    assert multibyte.status_code == 422


def test_register_accepts_password_of_72_bytes(client: TestClient) -> None:
    password = "A" * 72
    register = client.post(
        "/v1/auth/register",
        json={
            "email": "boundary@goldqueen.dev",
            "display_name": "Boundary",
            "password": password,
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/v1/auth/login",
        json={"email": "boundary@goldqueen.dev", "password": password},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_login_with_password_longer_than_72_bytes_is_rejected(
    client: TestClient,
) -> None:
    assert (
        client.post(
            "/v1/auth/register",
            json={
                "email": "short@goldqueen.dev",
                "display_name": "Short Password",
                "password": KNOWN_PASSWORD,
            },
        ).status_code
        == 201
    )
    response = client.post(
        "/v1/auth/login",
        json={"email": "short@goldqueen.dev", "password": "a" * 73},
    )
    assert response.status_code == 401

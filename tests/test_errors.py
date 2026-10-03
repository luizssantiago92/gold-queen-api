"""The public error body is one shape and never echoes submitted secrets."""

import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.exceptions import (
    INTERNAL_CODE,
    INTERNAL_DETAIL,
    VALIDATION_DETAIL,
    public_field_errors,
)
from app.main import app


def _reject_secret_keys(value: object) -> None:
    if isinstance(value, dict):
        assert "input" not in value
        assert "ctx" not in value
        for item in value.values():
            _reject_secret_keys(item)
    elif isinstance(value, list):
        for item in value:
            _reject_secret_keys(item)


def test_register_validation_does_not_echo_the_password(client: TestClient) -> None:
    password = "S3cret-Register-Password!"
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "not-an-email",
            "display_name": "Q",
            "password": password,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == VALIDATION_DETAIL
    assert body["code"] == "validation_error"
    assert isinstance(body["detail"], str)
    assert body["errors"]
    for error in body["errors"]:
        assert set(error) == {"loc", "msg", "type"}
    _reject_secret_keys(body)
    assert password not in response.text


def test_short_password_is_absent_from_the_validation_body(client: TestClient) -> None:
    password = "Pw9leak"
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "queen@goldqueen.dev",
            "display_name": "Gold Queen",
            "password": password,
        },
    )

    assert response.status_code == 422
    assert password not in response.text
    _reject_secret_keys(response.json())


def test_login_validation_does_not_echo_the_password(client: TestClient) -> None:
    password = "LoginSecretThatMustNotLeak!"
    response = client.post(
        "/v1/auth/login",
        json={"email": "not-an-email", "password": password},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert password not in response.text
    _reject_secret_keys(response.json())


def test_field_errors_drop_input_ctx_and_a_message_that_quotes_the_value() -> None:
    secret = "quoted-secret"
    cleaned = public_field_errors(
        [
            {
                "loc": ("body", 0, True, "password"),
                "msg": f"rejected {secret}",
                "type": "value_error",
                "input": secret,
                "ctx": {"hidden": secret},
            },
            {"loc": "password", "msg": "", "type": ""},
            "ignore-me",
        ]
    )

    assert cleaned == [
        {
            "loc": ["body", 0, "password"],
            "msg": "Invalid value",
            "type": "value_error",
        },
        {"loc": [], "msg": "Invalid value", "type": "value_error"},
    ]
    assert secret not in str(cleaned)


def test_missing_transaction_uses_the_domain_not_found_error(
    auth_client: TestClient,
) -> None:
    response = auth_client.get("/v1/dashboard/transactions/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Transaction not found.",
        "code": "not_found",
    }


def test_unknown_path_uses_the_error_contract(client: TestClient) -> None:
    response = client.get("/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found", "code": "not_found"}


def test_method_not_allowed_keeps_the_allow_header(client: TestClient) -> None:
    response = client.post("/health")

    assert response.status_code == 405
    assert response.json() == {
        "detail": "Method Not Allowed",
        "code": "method_not_allowed",
    }
    assert "GET" in response.headers["allow"]


def test_http_exception_keeps_www_authenticate(client: TestClient) -> None:
    def deny() -> None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    app.dependency_overrides[get_current_user] = deny
    try:
        response = client.get("/v1/auth/me")
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Not authenticated",
        "code": "unauthenticated",
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_structured_http_detail_is_not_echoed(client: TestClient) -> None:
    secret = "structured-secret"

    def deny() -> None:
        raise HTTPException(status_code=400, detail={"password": secret})

    app.dependency_overrides[get_current_user] = deny
    try:
        response = client.get("/v1/auth/me")
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 400
    assert response.json() == {"detail": "Request failed", "code": "bad_request"}
    assert secret not in response.text


def test_unmapped_http_status_still_has_a_code(client: TestClient) -> None:
    def teapot() -> None:
        raise HTTPException(status_code=418, detail="Short and stout")

    app.dependency_overrides[get_current_user] = teapot
    try:
        response = client.get("/v1/auth/me")
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.json() == {"detail": "Short and stout", "code": "http_error"}


def test_unexpected_error_is_generic_and_logged(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "db-password-hunter2"

    def explode(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError(secret)

    monkeypatch.setattr("app.routers.dashboard.treasury.total_balance", explode)

    with (
        TestClient(app, raise_server_exceptions=False) as raw,
        caplog.at_level(logging.ERROR, logger="app.core.exceptions"),
    ):
        raw.headers.update({"Authorization": auth_client.headers["Authorization"]})
        response = raw.get("/v1/dashboard/overview")

    assert response.status_code == 500
    assert response.json() == {"detail": INTERNAL_DETAIL, "code": INTERNAL_CODE}
    assert secret not in response.text
    assert "Traceback" not in response.text
    assert secret in caplog.text

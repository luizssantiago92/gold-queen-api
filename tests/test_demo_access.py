"""Shared demo account: read-only writes and a per-visitor AI quota."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.ai import AIEngine

ITEM_ID = "11111111-1111-4111-8111-111111111111"
DEMO_PASSWORD = "QueenDemo123!"


def _auth_headers(
    client: TestClient, email: str, password: str = DEMO_PASSWORD
) -> dict[str, str]:
    created = client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "display_name": "Demo Subject",
            "password": password,
        },
    )
    assert created.status_code == 201
    login = client.post(
        "/v1/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _with_ip(headers: dict[str, str], ip: str) -> dict[str, str]:
    return {**headers, "X-Real-IP": ip}


@pytest.mark.parametrize("email", ["queen@goldqueen.dev", "squire@goldqueen.dev"])
def test_demo_account_cannot_mutate_connections(
    client: TestClient, email: str
) -> None:
    headers = _auth_headers(client, email)

    connect = client.post("/v1/connections/connect", headers=headers)
    sync = client.post(
        "/v1/connections/sync", headers=headers, json={"item_id": ITEM_ID}
    )
    delete = client.delete("/v1/connections/1", headers=headers)

    for response in (connect, sync, delete):
        assert response.status_code == 403
        assert response.json() == {
            "detail": "The public demo account is read-only.",
            "code": "demo_read_only",
        }

    assert client.get("/v1/connections", headers=headers).json() == []


def test_demo_account_can_still_read_and_ask(
    client: TestClient,
) -> None:
    headers = _auth_headers(client, "queen@goldqueen.dev")

    assert client.get("/v1/auth/me", headers=headers).status_code == 200
    assert client.get("/v1/connections", headers=headers).status_code == 200
    assert client.get("/v1/dashboard/overview", headers=headers).status_code == 200
    tips = client.get("/v1/advisor/queen-tips", headers=headers)
    assert tips.status_code == 200
    chat = client.post(
        "/v1/chat/query",
        headers=headers,
        json={"question": "How can I protect my gold?"},
    )
    assert chat.status_code == 200


def test_demo_ai_quota_is_counted_per_client_ip(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "chat_daily_limit", 1)
    headers = _auth_headers(client, "queen@goldqueen.dev")
    first = _with_ip(headers, "203.0.113.10")
    second = _with_ip(headers, "203.0.113.20")

    assert (
        client.post(
            "/v1/chat/query",
            headers=first,
            json={"question": "How can I protect my gold today?"},
        ).status_code
        == 200
    )
    blocked = client.post(
        "/v1/chat/query",
        headers=first,
        json={"question": "How can I protect my gold tomorrow?"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limit_reached"

    other = client.post(
        "/v1/chat/query",
        headers=second,
        json={"question": "How should I budget my gold?"},
    )
    assert other.status_code == 200
    assert other.json()["remaining_requests"] == 0


def test_demo_cache_hit_reports_the_callers_own_remaining_quota(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "chat_daily_limit", 2)
    headers = _auth_headers(client, "queen@goldqueen.dev")
    question = {"question": "Should I save more gold this month?"}

    first = client.post(
        "/v1/chat/query", headers=_with_ip(headers, "203.0.113.10"), json=question
    ).json()
    second = client.post(
        "/v1/chat/query", headers=_with_ip(headers, "203.0.113.20"), json=question
    ).json()

    assert first["remaining_requests"] == 1
    assert second["from_cache"] is True
    assert second["remaining_requests"] == 2


def test_demo_quota_ignores_a_spoofed_real_ip_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "chat_daily_limit", 1)
    monkeypatch.setattr(settings, "login_trust_proxy_headers", False)
    headers = _auth_headers(client, "queen@goldqueen.dev")

    assert (
        client.post(
            "/v1/chat/query",
            headers=_with_ip(headers, "203.0.113.10"),
            json={"question": "How can I protect my gold?"},
        ).status_code
        == 200
    )
    blocked = client.post(
        "/v1/chat/query",
        headers=_with_ip(headers, "203.0.113.99"),
        json={"question": "How can I protect my gold again?"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limit_reached"


def test_normal_user_quota_stays_shared_across_client_ips(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "chat_daily_limit", 1)
    headers = _auth_headers(client, "knight@goldqueen.dev", "KnightDemo123!")

    assert (
        client.post(
            "/v1/chat/query",
            headers=_with_ip(headers, "203.0.113.10"),
            json={"question": "How can I protect my gold?"},
        ).status_code
        == 200
    )
    blocked = client.post(
        "/v1/chat/query",
        headers=_with_ip(headers, "198.51.100.8"),
        json={"question": "How should I budget my gold?"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limit_reached"


def test_demo_tips_share_the_visitor_chat_quota(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "chat_daily_limit", 1)
    headers = _with_ip(_auth_headers(client, "queen@goldqueen.dev"), "203.0.113.10")

    assert (
        client.post(
            "/v1/chat/query",
            headers=headers,
            json={"question": "How can I protect my gold?"},
        ).status_code
        == 200
    )
    tips = client.get("/v1/advisor/queen-tips", headers=headers)
    assert tips.status_code == 429
    assert tips.json()["code"] == "rate_limit_reached"


def test_a_failed_demo_answer_is_refunded_to_that_visitor(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "chat_daily_limit", 1)

    def broken(
        self: AIEngine, question: str, summary: str, locale: str = "en"
    ) -> tuple[str, bool]:
        return "The oracle is away.", False

    original = AIEngine.chat
    monkeypatch.setattr(AIEngine, "chat", broken)
    headers = _with_ip(_auth_headers(client, "queen@goldqueen.dev"), "203.0.113.10")
    question = {"question": "How can I protect my gold?"}

    failed = client.post("/v1/chat/query", headers=headers, json=question)
    assert failed.status_code == 200
    assert failed.json()["remaining_requests"] == 1

    monkeypatch.setattr(AIEngine, "chat", original)
    recovered = client.post(
        "/v1/chat/query",
        headers=headers,
        json={"question": "How should I budget my gold?"},
    )
    assert recovered.status_code == 200
    assert recovered.json()["remaining_requests"] == 0

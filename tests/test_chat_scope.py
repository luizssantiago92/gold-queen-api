"""Chat scope guard — off-topic questions must not consume quota."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.chat_scope import is_chat_in_scope, off_topic_reply


def test_in_scope_finance_questions() -> None:
    assert is_chat_in_scope("How can I protect my gold?")
    assert is_chat_in_scope("Quanto gastei com banquetes este mes?")
    assert is_chat_in_scope("Should I connect another bank?")


def test_out_of_scope_general_knowledge() -> None:
    assert not is_chat_in_scope("What is the capital of France?")
    assert not is_chat_in_scope("Write a Python script for me")
    assert not is_chat_in_scope("Tell me a joke about dragons")


def test_off_topic_chat_does_not_consume_quota(auth_client: TestClient) -> None:
    before = auth_client.post(
        "/v1/chat/query",
        json={"question": "What is the weather today?", "locale": "en"},
    )
    assert before.status_code == 200
    body = before.json()
    assert body["remaining_requests"] == get_settings().chat_daily_limit
    assert "treasury" in body["answer"].lower()


def test_off_topic_portuguese_reply(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/v1/chat/query",
        json={"question": "Conte uma piada", "locale": "pt"},
    )
    assert "tesouro" in response.json()["answer"].lower()


def test_off_topic_reply_messages() -> None:
    assert "treasury" in off_topic_reply("en").lower()
    assert "tesouro" in off_topic_reply("pt").lower()

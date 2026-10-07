"""Chat scope guard — off-topic questions must not consume quota."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.chat_scope import (
    _IN_SCOPE_FOLDED,
    _OUT_OF_SCOPE_FOLDED,
    _fold_match_text,
    is_chat_in_scope,
    off_topic_reply,
)


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


def test_accented_treasury_questions_stay_in_scope() -> None:
    accented = "Quais foram minhas 3 maiores transações este mês?"
    assert is_chat_in_scope(accented)
    assert is_chat_in_scope("Quais foram minhas 3 maiores transacoes este mes?")
    assert is_chat_in_scope("QUAIS FORAM MINHAS 3 MAIORES TRANSAÇÕES ESTE MÊS?")
    assert is_chat_in_scope("Qual foi meu maior gasto?")
    assert is_chat_in_scope("QUAL FOI MEU MAIOR GASTO?")


def test_english_transaction_questions_stay_in_scope() -> None:
    assert is_chat_in_scope("What were my 3 largest transactions this month?")
    assert is_chat_in_scope("WHAT WAS MY BIGGEST EXPENSE?")
    assert is_chat_in_scope("What were my 3 largest transactions this month?".upper())


def test_accented_off_topic_questions_stay_refused() -> None:
    assert not is_chat_in_scope("   ")
    assert not is_chat_in_scope("Qual é a capital da França?")
    assert not is_chat_in_scope("QUAL É A CAPITAL DA FRANÇA?")
    assert not is_chat_in_scope("Escreva código para mim")
    assert not is_chat_in_scope("Conte uma piada sobre o clima")


def test_keyword_lists_are_folded_like_the_question() -> None:
    assert _fold_match_text("Transações") == "transacoes"
    assert _fold_match_text("MÊS") == "mes"
    assert _fold_match_text("quem é ") == "quem e "
    assert "mes" in _IN_SCOPE_FOLDED
    assert "transac" in _IN_SCOPE_FOLDED
    assert "quem e " in _OUT_OF_SCOPE_FOLDED

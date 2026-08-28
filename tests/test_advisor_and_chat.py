"""Queen's Tips and Master of Coin chatbot tests (RF04, RF05)."""

from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_queen_tips_returns_three_sections(auth_client: TestClient) -> None:
    auth_client.post("/v1/connections/sync", json={"item_id": "item-alpha"})

    body = auth_client.get("/v1/advisor/queen-tips").json()
    assert body["critical_expense"]
    assert body["management_status"]
    assert body["smart_guidance"]


def test_chat_answers_and_reports_quota(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/v1/chat/query", json={"question": "Como protejo meu ouro?"}
    )
    assert response.status_code == 200

    body = response.json()
    assert body["answer"]
    assert body["from_cache"] is False
    assert body["daily_limit"] == get_settings().chat_daily_limit


def test_identical_question_hits_the_cache(auth_client: TestClient) -> None:
    question = {"question": "Devo cortar gastos com banquetes?"}

    first = auth_client.post("/v1/chat/query", json=question).json()
    second = auth_client.post("/v1/chat/query", json=question).json()

    assert second["from_cache"] is True
    assert second["answer"] == first["answer"]
    # A cached answer must not consume another interaction.
    assert second["remaining_requests"] == first["remaining_requests"]


def test_daily_quota_returns_themed_429(auth_client: TestClient) -> None:
    limit = get_settings().chat_daily_limit

    for index in range(limit):
        response = auth_client.post(
            "/v1/chat/query", json={"question": f"Pergunta numero {index}"}
        )
        assert response.status_code == 200

    blocked = auth_client.post(
        "/v1/chat/query", json={"question": "Uma pergunta a mais"}
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limit_reached"
    assert "Rainha" in blocked.json()["detail"]


def test_health_endpoint(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"

"""The AI grounding context must carry the product rules (see RF04/RF05)."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import get_settings
from app.services.treasury import build_ai_summary


def _seed_user(client: TestClient) -> int:
    client.post(
        "/v1/auth/register",
        json={
            "email": "summary@goldqueen.dev",
            "display_name": "Summary",
            "password": "StrongPass123!",
        },
    )
    return 1


def test_summary_states_the_connection_and_chat_limits(
    client: TestClient, session: Session
) -> None:
    user_id = _seed_user(client)
    settings = get_settings()

    summary = build_ai_summary(session, user_id)

    # Without these the model invents its own limits when asked about the plan.
    assert f"up to {settings.max_bank_connections} bank connections" in summary
    assert f"{settings.chat_daily_limit} questions per day" in summary


def test_summary_lists_connected_banks(client: TestClient, session: Session) -> None:
    _seed_user(client)
    login = client.post(
        "/v1/auth/login",
        json={"email": "summary@goldqueen.dev", "password": "StrongPass123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/v1/connections/sync", json={"item_id": "item-summary"}, headers=headers
    )

    summary = build_ai_summary(session, 1)
    assert "no banks connected yet" not in summary
    assert "Connected banks (1 of" in summary

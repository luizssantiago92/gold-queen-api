"""Daily token bucket for Gold Queen interactions (RF05).

The counter lives in PostgreSQL so the quota survives restarts and multiple
workers, which an in-memory ``lru_cache`` alone could not guarantee.
"""

from datetime import date

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.models.entities import ChatUsage

QUEEN_QUOTA_MESSAGE = (
    "A Rainha precisa recolher-se aos seus aposentos para balancear o tesouro real. "
    "Retorne em 24 horas para novos conselhos sobre o seu ouro."
)


def _get_or_create_usage(session: Session, user_id: int, usage_date: date) -> ChatUsage:
    usage = session.exec(
        select(ChatUsage).where(
            ChatUsage.user_id == user_id, ChatUsage.usage_date == usage_date
        )
    ).first()
    if usage is None:
        usage = ChatUsage(user_id=user_id, usage_date=usage_date, request_count=0)
        session.add(usage)
        session.commit()
        session.refresh(usage)
    return usage


def remaining_requests(session: Session, user_id: int) -> int:
    limit = get_settings().chat_daily_limit
    usage = _get_or_create_usage(session, user_id, date.today())
    return max(limit - usage.request_count, 0)


def consume_request(session: Session, user_id: int) -> int:
    """Consume one daily interaction or raise ``RateLimitError``."""
    limit = get_settings().chat_daily_limit
    usage = _get_or_create_usage(session, user_id, date.today())

    if usage.request_count >= limit:
        raise RateLimitError(QUEEN_QUOTA_MESSAGE)

    usage.request_count += 1
    session.add(usage)
    session.commit()
    session.refresh(usage)
    return max(limit - usage.request_count, 0)

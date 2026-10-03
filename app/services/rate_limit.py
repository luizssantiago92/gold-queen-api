"""Daily token bucket for Gold Queen interactions (RF05).

The counter lives in PostgreSQL so the quota survives restarts and multiple
workers, which an in-memory ``lru_cache`` alone could not guarantee.
"""

from datetime import date

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.core.locale import DEFAULT_LOCALE, Locale
from app.models.entities import ChatUsage, DemoChatUsage

QUEEN_QUOTA_MESSAGES: dict[Locale, str] = {
    "en": (
        "The Queen must retire to her chambers to balance the royal treasury. "
        "Return in 24 hours for new counsel about your gold."
    ),
    "pt": (
        "A Rainha precisa recolher-se aos seus aposentos para balancear "
        "o tesouro real. "
        "Retorne em 24 horas para novos conselhos sobre o seu ouro."
    ),
}


def _get_or_create_usage(
    session: Session, user_id: int, usage_date: date, subject_key: str = ""
) -> ChatUsage | DemoChatUsage:
    """Normal users share one row. A non-empty subject is a demo visitor."""
    if subject_key:
        demo_usage = session.exec(
            select(DemoChatUsage).where(
                DemoChatUsage.user_id == user_id,
                DemoChatUsage.usage_date == usage_date,
                DemoChatUsage.subject_key == subject_key,
            )
        ).first()
        if demo_usage is None:
            demo_usage = DemoChatUsage(
                user_id=user_id,
                usage_date=usage_date,
                subject_key=subject_key,
                request_count=0,
            )
            session.add(demo_usage)
            session.commit()
            session.refresh(demo_usage)
        return demo_usage

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


def remaining_requests(session: Session, user_id: int, subject_key: str = "") -> int:
    limit = get_settings().chat_daily_limit
    usage = _get_or_create_usage(session, user_id, date.today(), subject_key)
    return max(limit - usage.request_count, 0)


def refund_request(session: Session, user_id: int, subject_key: str = "") -> int:
    """Give a consumed interaction back when the model never answered."""
    limit = get_settings().chat_daily_limit
    usage = _get_or_create_usage(session, user_id, date.today(), subject_key)

    if usage.request_count > 0:
        usage.request_count -= 1
        session.add(usage)
        session.commit()
        session.refresh(usage)

    return max(limit - usage.request_count, 0)


def consume_request(
    session: Session,
    user_id: int,
    locale: Locale = DEFAULT_LOCALE,
    subject_key: str = "",
) -> int:
    """Consume one daily interaction or raise ``RateLimitError``."""
    limit = get_settings().chat_daily_limit
    usage = _get_or_create_usage(session, user_id, date.today(), subject_key)

    if usage.request_count >= limit:
        raise RateLimitError(QUEEN_QUOTA_MESSAGES[locale])

    usage.request_count += 1
    session.add(usage)
    session.commit()
    session.refresh(usage)
    return max(limit - usage.request_count, 0)

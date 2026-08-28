"""RF05 - Master of Coin chatbot with daily cache and quota."""

import hashlib
from datetime import date

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import AIDep, CurrentUser, SessionDep
from app.core.config import get_settings
from app.models.entities import ChatCache
from app.schemas.advisor import ChatRequest, ChatResponse
from app.services import rate_limit, treasury

router = APIRouter(prefix="/v1/chat", tags=["chat"])


def _normalize(question: str) -> str:
    return " ".join(question.lower().split())


@router.post("/query", response_model=ChatResponse)
def query(
    payload: ChatRequest,
    current_user: CurrentUser,
    session: SessionDep,
    ai: AIDep,
) -> ChatResponse:
    user_id: int = current_user.id  # type: ignore[assignment]
    settings = get_settings()
    today = date.today()
    question_hash = hashlib.sha256(_normalize(payload.question).encode()).hexdigest()

    cached = session.exec(
        select(ChatCache).where(
            ChatCache.user_id == user_id,
            ChatCache.question_hash == question_hash,
            ChatCache.usage_date == today,
        )
    ).first()

    # An identical question on the same day costs no tokens and no quota.
    if cached is not None:
        return ChatResponse(
            answer=cached.answer,
            from_cache=True,
            remaining_requests=rate_limit.remaining_requests(session, user_id),
            daily_limit=settings.chat_daily_limit,
        )

    remaining = rate_limit.consume_request(session, user_id)
    summary = treasury.build_ai_summary(session, user_id)
    answer = ai.chat(payload.question, summary)

    session.add(
        ChatCache(
            user_id=user_id,
            question_hash=question_hash,
            question=payload.question,
            answer=answer,
            usage_date=today,
        )
    )
    session.commit()

    return ChatResponse(
        answer=answer,
        from_cache=False,
        remaining_requests=remaining,
        daily_limit=settings.chat_daily_limit,
    )

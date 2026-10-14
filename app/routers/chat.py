"""RF05 - Master of Coin chatbot with daily cache and quota."""

import hashlib
from datetime import date

from fastapi import APIRouter, Request
from sqlmodel import select

from app.api.deps import AIDep, CurrentUser, SessionDep
from app.core.config import get_settings
from app.models.entities import ChatCache, require_id
from app.schemas.advisor import ChatRequest, ChatResponse, TransactionSource
from app.schemas.errors import error_responses
from app.services import rate_limit, treasury
from app.services.chat_scope import is_chat_in_scope, off_topic_reply
from app.services.demo_access import demo_quota_subject
from app.services.grounding import (
    GroundedTransaction,
    asks_for_largest_expense,
    format_grounding_block,
    largest_expense_answer,
    select_grounding_sources,
)

router = APIRouter(prefix="/v1/chat", tags=["chat"])


def _normalize(question: str) -> str:
    return " ".join(question.lower().split())


def _response_sources(rows: list[GroundedTransaction]) -> list[TransactionSource]:
    return [TransactionSource.model_validate(row, from_attributes=True) for row in rows]


@router.post(
    "/query",
    response_model=ChatResponse,
    summary="Ask the Queen",
    description=(
        "Answer one treasury question, list the transactions used to build "
        "the answer, and report the remaining daily quota."
    ),
    responses=error_responses(
        (401, "The bearer token is missing or invalid."),
        (422, "The question failed validation."),
        (429, "The shared daily Queen quota is exhausted."),
    ),
)
def query(
    payload: ChatRequest,
    current_user: CurrentUser,
    session: SessionDep,
    ai: AIDep,
    request: Request,
) -> ChatResponse:
    user_id = require_id(current_user.id)
    subject_key = demo_quota_subject(current_user, request)
    settings = get_settings()
    today = date.today()

    if not is_chat_in_scope(payload.question):
        return ChatResponse(
            answer=off_topic_reply(payload.locale),
            from_cache=False,
            remaining_requests=rate_limit.remaining_requests(
                session, user_id, subject_key
            ),
            daily_limit=settings.chat_daily_limit,
            sources=[],
        )

    selected = select_grounding_sources(session, user_id, payload.question)
    grounding = format_grounding_block(selected)
    # The cache key includes the grounding block so a hit still names the
    # movements that were in the prompt. A sync that changes those movements
    # is a different question and spends a new unit.
    question_hash = hashlib.sha256(
        f"{_normalize(payload.question)}\n{grounding}".encode()
    ).hexdigest()
    # An identical question with the same movements costs no tokens and no quota.
    cached = session.exec(
        select(ChatCache).where(
            ChatCache.user_id == user_id,
            ChatCache.question_hash == question_hash,
            ChatCache.usage_date == today,
        )
    ).first()
    if cached is not None:
        return ChatResponse(
            answer=cached.answer,
            from_cache=True,
            remaining_requests=rate_limit.remaining_requests(
                session, user_id, subject_key
            ),
            daily_limit=settings.chat_daily_limit,
            sources=_response_sources(selected),
        )

    remaining = rate_limit.consume_request(
        session, user_id, payload.locale, subject_key
    )
    # The largest expense is already the selected rows. Calling the model
    # here retries a 30 second timeout three times, then drops those rows.
    if asks_for_largest_expense(payload.question):
        answer = largest_expense_answer(selected, payload.locale)
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
            sources=_response_sources(selected),
        )

    summary = treasury.build_ai_summary(session, user_id)
    answer, answered = ai.chat(
        payload.question, f"{summary}\n\n{grounding}", payload.locale
    )

    # Caching the fallback would keep serving a generic reply for the rest of the
    # day, long after the model recovered, so an outage costs neither the cache
    # slot nor one of the user's daily questions.
    if answered:
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
    else:
        remaining = rate_limit.refund_request(session, user_id, subject_key)

    return ChatResponse(
        answer=answer,
        from_cache=False,
        remaining_requests=remaining,
        daily_limit=settings.chat_daily_limit,
        sources=_response_sources(selected) if answered else [],
    )

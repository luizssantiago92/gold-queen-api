"""Queen's Tips: a daily treasury diagnosis with a summary cache and a shared quota."""

import hashlib
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Header, Query, Request
from pydantic import ValidationError
from sqlmodel import col, select

from app.api.deps import AIDep, CurrentUser, SessionDep
from app.core.ai_guardrails import QueenTips
from app.core.locale import Locale, parse_accept_language, parse_locale
from app.models.entities import ChatCache, require_id
from app.schemas.advisor import QueenTipsResponse
from app.schemas.errors import error_responses
from app.services import rate_limit, treasury
from app.services.demo_access import demo_quota_subject

router = APIRouter(prefix="/v1/advisor", tags=["advisor"])

_TIPS_CACHE_KEY = "queen-tips"


def _tips_from_cached_answer(answer: str) -> QueenTips | None:
    """Return cached tips, or None when the row is not current JSON.

    Older rows joined the three fields with a newline separator. Text that
    contained that separator could not be split into three values. Those rows
    are a cache miss and are replaced the next time a guarded answer is stored.
    """
    try:
        return QueenTips.model_validate_json(answer)
    except ValidationError:
        return None


@router.get(
    "/queen-tips",
    response_model=QueenTipsResponse,
    summary="Queen's Tips",
    description=(
        "Return today's diagnosis. A cached result for the same treasury "
        "summary spends no quota."
    ),
    responses=error_responses(
        (401, "The bearer token is missing or invalid."),
        (422, "locale is not a supported language."),
        (429, "The shared daily Queen quota is exhausted."),
    ),
)
def queen_tips(
    current_user: CurrentUser,
    session: SessionDep,
    ai: AIDep,
    request: Request,
    locale: Annotated[Locale | None, Query()] = None,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> QueenTipsResponse:
    """Return today's Queen's Tips for the signed-in treasury.

    The language comes from the locale query when it is set, otherwise from
    Accept-Language. A same-day cache hit is keyed by the treasury summary,
    so a repeat of the same summary spends no model call and no daily quota.
    Tips the guardrail rejects are not cached. The call shares that quota
    with chat. Demo visitors are counted per IP.
    """
    resolved_locale = (
        parse_locale(locale)
        if locale is not None
        else parse_accept_language(accept_language)
    )
    user_id = require_id(current_user.id)
    subject_key = demo_quota_subject(current_user, request)
    summary = treasury.build_ai_summary(session, user_id)

    # The cache key includes the summary so a new sync produces fresh advice.
    question_hash = hashlib.sha256(f"{_TIPS_CACHE_KEY}:{summary}".encode()).hexdigest()
    today = date.today()

    cached = session.exec(
        select(ChatCache)
        .where(
            ChatCache.user_id == user_id,
            ChatCache.question_hash == question_hash,
            ChatCache.usage_date == today,
        )
        .order_by(col(ChatCache.id).desc())
    ).first()

    if cached is not None:
        cached_tips = _tips_from_cached_answer(cached.answer)
        if cached_tips is not None:
            return QueenTipsResponse(
                critical_expense=cached_tips.critical_expense,
                management_status=cached_tips.management_status,
                smart_guidance=cached_tips.smart_guidance,
                is_guarded=True,
                from_cache=True,
            )

    rate_limit.consume_request(session, user_id, resolved_locale, subject_key)
    tips, guarded = ai.queen_tips(summary, resolved_locale)

    if guarded:
        payload = tips.model_dump_json()
        if cached is None:
            session.add(
                ChatCache(
                    user_id=user_id,
                    question_hash=question_hash,
                    question=_TIPS_CACHE_KEY,
                    answer=payload,
                    usage_date=today,
                )
            )
        else:
            cached.answer = payload
            session.add(cached)
        session.commit()

    return QueenTipsResponse(
        critical_expense=tips.critical_expense,
        management_status=tips.management_status,
        smart_guidance=tips.smart_guidance,
        is_guarded=guarded,
        from_cache=False,
    )

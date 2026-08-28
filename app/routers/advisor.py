"""RF04 - Queen's Tips: proactive financial diagnosis."""

import hashlib
from datetime import date

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import AIDep, CurrentUser, SessionDep
from app.models.entities import ChatCache
from app.schemas.advisor import QueenTipsResponse
from app.services import rate_limit, treasury

router = APIRouter(prefix="/v1/advisor", tags=["advisor"])

_TIPS_CACHE_KEY = "queen-tips"


@router.get("/queen-tips", response_model=QueenTipsResponse)
def queen_tips(
    current_user: CurrentUser, session: SessionDep, ai: AIDep
) -> QueenTipsResponse:
    """Return today's diagnosis, reusing the cached one to spend zero extra tokens."""
    user_id: int = current_user.id  # type: ignore[assignment]
    summary = treasury.build_ai_summary(session, user_id)

    # The cache key includes the summary so a new sync produces fresh advice.
    question_hash = hashlib.sha256(
        f"{_TIPS_CACHE_KEY}:{summary}".encode()
    ).hexdigest()
    today = date.today()

    cached = session.exec(
        select(ChatCache).where(
            ChatCache.user_id == user_id,
            ChatCache.question_hash == question_hash,
            ChatCache.usage_date == today,
        )
    ).first()

    if cached is not None:
        critical, management, guidance = cached.answer.split("\n||\n")
        return QueenTipsResponse(
            critical_expense=critical,
            management_status=management,
            smart_guidance=guidance,
            is_guarded=True,
            from_cache=True,
        )

    rate_limit.consume_request(session, user_id)
    tips, guarded = ai.queen_tips(summary)

    if guarded:
        session.add(
            ChatCache(
                user_id=user_id,
                question_hash=question_hash,
                question=_TIPS_CACHE_KEY,
                answer="\n||\n".join(
                    [tips.critical_expense, tips.management_status, tips.smart_guidance]
                ),
                usage_date=today,
            )
        )
        session.commit()

    return QueenTipsResponse(
        critical_expense=tips.critical_expense,
        management_status=tips.management_status,
        smart_guidance=tips.smart_guidance,
        is_guarded=guarded,
        from_cache=False,
    )

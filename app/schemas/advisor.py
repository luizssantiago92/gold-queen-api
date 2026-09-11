"""Queen's Tips and Gold Queen chat payloads (RF04, RF05)."""

from pydantic import BaseModel, Field

from app.core.locale import DEFAULT_LOCALE, Locale


class QueenTipsResponse(BaseModel):
    critical_expense: str
    management_status: str
    smart_guidance: str
    is_guarded: bool
    from_cache: bool


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    locale: Locale = DEFAULT_LOCALE


class ChatResponse(BaseModel):
    answer: str
    from_cache: bool
    remaining_requests: int
    daily_limit: int

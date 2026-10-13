"""Queen's Tips and Gold Queen chat payloads (RF04, RF05)."""

from datetime import date as Date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.locale import DEFAULT_LOCALE, Locale


class TransactionSource(BaseModel):
    """One movement that was placed in the grounding context for an answer."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 12,
                    "date": "2026-08-24",
                    "description": "NETFLIX.COM",
                    "amount": "-100.00",
                    "category": "CreditCard",
                    "account": "Mastercard Black",
                }
            ]
        }
    )

    id: int = Field(description="Transaction id.")
    date: Date = Field(description="Transaction date.")
    description: str = Field(description="Transaction description.")
    amount: Decimal = Field(description="Signed amount. A negative value is money out.")
    category: str = Field(
        description=(
            "Display category for this movement, "
            "the same bucket the treasury charts use."
        )
    )
    account: str = Field(description="Account name that holds the movement.")


class QueenTipsResponse(BaseModel):
    critical_expense: str
    management_status: str
    smart_guidance: str
    is_guarded: bool
    from_cache: bool
    sources: list[TransactionSource] = Field(
        description=(
            "Current-month transactions placed in the grounding context for "
            "this diagnosis. A bank card-bill settlement is omitted."
        )
    )


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    locale: Locale = DEFAULT_LOCALE


class ChatResponse(BaseModel):
    answer: str
    from_cache: bool
    remaining_requests: int
    daily_limit: int
    sources: list[TransactionSource] = Field(
        description=(
            "Transactions placed in the grounding context for this answer. "
            "Empty when the reply is an off-topic refusal or the model did not answer."
        )
    )

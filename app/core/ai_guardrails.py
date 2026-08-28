"""Runtime guardrails for LLM output.

Every AI response is parsed and validated against a strict Pydantic schema before
it reaches the database or the client. Anything the model invents outside the
contract is rejected, and the caller falls back to a deterministic result flagged
with ``is_guarded=False`` so the UI can audit it.
"""

import json
import re
from typing import TypeVar

from pydantic import BaseModel, Field, ValidationError, field_validator

TModel = TypeVar("TModel", bound=BaseModel)

_JSON_BLOCK = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)

# Closed vocabulary: the model may not invent categories.
ALLOWED_CATEGORIES: tuple[str, ...] = (
    "Food",
    "Transport",
    "Housing",
    "Health",
    "Education",
    "Entertainment",
    "Shopping",
    "Bills",
    "Income",
    "Transfer",
    "Other",
)


class GuardrailViolation(Exception):
    """Raised when the model output cannot be coerced into the expected schema."""


class CategorizedTransaction(BaseModel):
    """Strict contract for RF02 categorization."""

    transaction_id: str
    category: str

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, value: str) -> str:
        normalized = value.strip().title()
        if normalized not in ALLOWED_CATEGORIES:
            raise ValueError(f"Unknown category: {value}")
        return normalized


class CategorizationBatch(BaseModel):
    results: list[CategorizedTransaction] = Field(default_factory=list)


class QueenTips(BaseModel):
    """Strict contract for RF04 structured advice."""

    critical_expense: str = Field(min_length=1, max_length=600)
    management_status: str = Field(min_length=1, max_length=600)
    smart_guidance: str = Field(min_length=1, max_length=900)


def extract_json(raw_output: str) -> object:
    """Pull the first JSON object/array out of a raw model response."""
    if not raw_output or not raw_output.strip():
        raise GuardrailViolation("Model returned an empty response.")

    candidate = raw_output.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`").removeprefix("json").strip()

    match = _JSON_BLOCK.search(candidate)
    if not match:
        raise GuardrailViolation("Model response contained no JSON payload.")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise GuardrailViolation(f"Model returned malformed JSON: {exc}") from exc


def validate_output(raw_output: str, schema: type[TModel]) -> TModel:
    """Parse and validate a raw model response, or raise GuardrailViolation."""
    payload = extract_json(raw_output)
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise GuardrailViolation(f"Model output violated the schema: {exc}") from exc

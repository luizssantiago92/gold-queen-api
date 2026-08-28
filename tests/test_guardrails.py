"""Guardrail validation tests (RF02)."""

import pytest

from app.core.ai_guardrails import (
    CategorizationBatch,
    GuardrailViolation,
    QueenTips,
    validate_output,
)


def test_valid_categorization_passes() -> None:
    raw = '{"results": [{"transaction_id": "tx-1", "category": "Food"}]}'
    batch = validate_output(raw, CategorizationBatch)
    assert batch.results[0].category == "Food"


def test_category_is_normalized() -> None:
    raw = '{"results": [{"transaction_id": "tx-1", "category": "  food "}]}'
    assert validate_output(raw, CategorizationBatch).results[0].category == "Food"


def test_json_wrapped_in_markdown_fence_is_accepted() -> None:
    raw = '```json\n{"results": [{"transaction_id": "tx-9", "category": "Transport"}]}\n```'
    assert validate_output(raw, CategorizationBatch).results[0].category == "Transport"


def test_hallucinated_category_is_rejected() -> None:
    raw = '{"results": [{"transaction_id": "tx-1", "category": "DragonInsurance"}]}'
    with pytest.raises(GuardrailViolation):
        validate_output(raw, CategorizationBatch)


def test_malformed_json_is_rejected() -> None:
    with pytest.raises(GuardrailViolation):
        validate_output("{not json at all", CategorizationBatch)


def test_empty_output_is_rejected() -> None:
    with pytest.raises(GuardrailViolation):
        validate_output("   ", CategorizationBatch)


def test_queen_tips_requires_all_three_sections() -> None:
    with pytest.raises(GuardrailViolation):
        validate_output('{"critical_expense": "only one field"}', QueenTips)

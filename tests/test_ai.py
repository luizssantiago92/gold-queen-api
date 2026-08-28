"""AI engine behaviour that must hold without calling the provider."""

from decimal import Decimal

from app.services.ai import _is_transient, get_ai_engine


def test_transient_errors_are_detected() -> None:
    assert _is_transient(Exception("503 UNAVAILABLE. model is busy"))
    assert _is_transient(Exception("429 RESOURCE_EXHAUSTED"))


def test_permanent_errors_are_not_retried() -> None:
    assert not _is_transient(Exception("404 NOT_FOUND. model does not exist"))
    assert not _is_transient(Exception("401 UNAUTHENTICATED. bad api key"))


def test_fallback_categorization_is_never_guarded() -> None:
    """Without an API key the engine must still categorize, but unguarded."""
    engine = get_ai_engine()
    assert engine.enabled is False

    mapping, guarded = engine.categorize(
        [
            ("tx-1", "Padaria do Reino", Decimal("-42.90")),
            ("tx-2", "Carruagem Express", Decimal("-88.00")),
            ("tx-3", "Soldo Real", Decimal("5200.00")),
        ]
    )

    assert guarded is False
    assert mapping["tx-1"] == "Food"
    assert mapping["tx-2"] == "Transport"
    assert mapping["tx-3"] == "Income"


def test_empty_batch_is_a_noop() -> None:
    assert get_ai_engine().categorize([]) == ({}, False)

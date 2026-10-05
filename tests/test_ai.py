"""AI engine behaviour that must hold without calling the provider."""

from decimal import Decimal

import pytest

from app.providers.base import Completion, ProviderError
from app.services.ai import (
    _MAX_RETRY_DELAY_SECONDS,
    AIEngine,
    _fallback_chat,
    _is_transient,
    _retry_delay_seconds,
    get_ai_engine,
)


def test_transient_errors_are_detected() -> None:
    assert _is_transient(Exception("503 UNAVAILABLE. model is busy"))
    assert _is_transient(Exception("429 RESOURCE_EXHAUSTED"))
    assert _is_transient(ProviderError("timeout", timed_out=True))
    assert _is_transient(ProviderError("slow", status_code=429))


def test_429_is_retried_and_honors_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(
        "app.services.ai.time.sleep", lambda seconds: sleeps.append(seconds)
    )

    class _Flaky:
        name = "flaky"

        def __init__(self) -> None:
            self.calls = 0

        def complete(
            self,
            messages: list[dict[str, str]],
            temperature: float,
            max_tokens: int | None,
        ) -> Completion:
            self.calls += 1
            if self.calls == 1:
                raise ProviderError("slow", status_code=429, retry_after_seconds=30)
            return Completion(content="ready", model="fake", provider=self.name)

        def health(self) -> bool:
            return True

    provider = _Flaky()
    assert AIEngine(provider)._generate("prompt", "system") == "ready"
    assert provider.calls == 2
    assert sleeps == [_MAX_RETRY_DELAY_SECONDS]


def test_retry_delay_uses_backoff_without_retry_after() -> None:
    assert _retry_delay_seconds(ProviderError("down", status_code=503), 0) == 1.5


def test_permanent_errors_are_not_retried() -> None:
    assert not _is_transient(Exception("404 NOT_FOUND. model does not exist"))
    assert not _is_transient(Exception("401 UNAUTHENTICATED. bad api key"))
    assert not _is_transient(ProviderError("bad key", status_code=400))


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


def test_fallback_chat_respects_locale() -> None:
    en = _fallback_chat("How do I save?", "en")
    pt = _fallback_chat("Como poupo?", "pt")
    assert "Noble subject" in en
    assert "Nobre subdito" in pt

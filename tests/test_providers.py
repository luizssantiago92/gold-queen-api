"""Provider adapter tests (llm-router-gateway patterns)."""

from app.providers.base import ProviderError
from app.providers.fake import FakeProvider
from app.providers.gemini import _messages_to_gemini


def test_fake_provider_returns_configured_content() -> None:
    provider = FakeProvider("test", content='{"ok": true}')
    result = provider.complete([{"role": "user", "content": "hello"}], 0.2, None)
    assert result.content == '{"ok": true}'
    assert provider.calls == 1


def test_fake_provider_raises_configured_error() -> None:
    provider = FakeProvider(
        "test",
        error=ProviderError("upstream down", status_code=503),
    )
    try:
        provider.complete([{"role": "user", "content": "hello"}], 0.2, None)
        raise AssertionError("expected ProviderError")
    except ProviderError as exc:
        assert exc.is_retryable


def test_messages_to_gemini_splits_system_instruction() -> None:
    system, contents = _messages_to_gemini(
        [
            {"role": "system", "content": "Be precise."},
            {"role": "user", "content": "Categorize this."},
        ]
    )
    assert system == "Be precise."
    assert contents == [{"role": "user", "parts": [{"text": "Categorize this."}]}]

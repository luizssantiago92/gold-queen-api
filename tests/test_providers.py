"""Provider adapter tests (llm-router-gateway patterns)."""

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx

from app.providers.base import ProviderError
from app.providers.fake import FakeProvider
from app.providers.gemini import (
    GeminiProvider,
    _messages_to_gemini,
    _retry_after_seconds,
)


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


def test_provider_error_treats_429_as_retryable() -> None:
    assert ProviderError("slow", status_code=429).is_retryable
    assert not ProviderError("bad key", status_code=401).is_retryable
    assert ProviderError("upstream", status_code=503).is_retryable


def test_gemini_sends_the_api_key_in_a_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        )

    provider = GeminiProvider(
        "super-secret",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = provider.complete([{"role": "user", "content": "hello"}], 0.2, None)
    assert result.content == "ok"
    assert seen[0].headers["x-goog-api-key"] == "super-secret"
    assert "key" not in seen[0].url.params
    assert "super-secret" not in str(seen[0].url)


def test_gemini_429_exposes_retry_after() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "2.5"})

    provider = GeminiProvider(
        "super-secret",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    try:
        provider.complete([{"role": "user", "content": "hello"}], 0.2, None)
        raise AssertionError("expected ProviderError")
    except ProviderError as exc:
        assert exc.status_code == 429
        assert exc.is_retryable
        assert exc.retry_after_seconds == 2.5


def test_retry_after_http_date_is_parsed() -> None:
    moment = datetime.now(UTC) + timedelta(seconds=3)
    headers = httpx.Headers({"retry-after": format_datetime(moment, usegmt=True)})
    parsed = _retry_after_seconds(headers)
    assert parsed is not None
    assert 0 <= parsed <= 5


def test_messages_to_gemini_splits_system_instruction() -> None:
    system, contents = _messages_to_gemini(
        [
            {"role": "system", "content": "Be precise."},
            {"role": "user", "content": "Categorize this."},
        ]
    )
    assert system == "Be precise."
    assert contents == [{"role": "user", "parts": [{"text": "Categorize this."}]}]

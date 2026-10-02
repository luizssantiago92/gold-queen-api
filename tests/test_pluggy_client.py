"""Pluggy HTTP client tests.

Production sync broke because Pluggy retired ``GET /transactions`` in favour of
``GET /v2/transactions`` with cursor pagination. The local simulator hid it: it
never issues a request, so the whole suite passed against a dead endpoint. These
tests pin the wire contract instead of the simulated behaviour.
"""

import logging
from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

import httpx
import pytest

from app.core.exceptions import UpstreamError
from app.services.pluggy import PluggyClient, _item_url


def _live_client(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> PluggyClient:
    """A client whose requests are answered by ``handler``.

    Credentials are set so the client takes the HTTP path: without them it
    answers from its offline simulator and never performs a request. They go
    through monkeypatch because settings are a cached singleton — assigning
    directly would leave Pluggy enabled for every later test.
    """
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def patched(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched)

    client = PluggyClient()
    monkeypatch.setattr(client._settings, "pluggy_client_id", "id")
    monkeypatch.setattr(client._settings, "pluggy_client_secret", "secret")
    return client


@pytest.mark.asyncio
async def test_transactions_use_the_v2_endpoint_and_follow_the_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[httpx.URL] = []
    page_2 = "https://api.pluggy.ai/v2/transactions?accountId=acc-1&cursor=abc"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "key"})

        seen.append(request.url)

        if request.url.params.get("cursor") is None:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"id": "t1", "description": "Padaria", "amount": -10.5,
                         "date": "2026-08-02T00:00:00.000Z"}
                    ],
                    "next": page_2,
                },
            )
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "t2", "description": "Soldo", "amount": 4200,
                     "date": "2026-08-01T00:00:00.000Z"}
                ],
                "next": None,
            },
        )

    client = _live_client(monkeypatch, handler)
    transactions = await client.fetch_transactions("acc-1")

    assert [url.path for url in seen] == ["/v2/transactions", "/v2/transactions"]
    # The second call must follow the "next" URL verbatim, cursor included.
    assert str(seen[1]) == page_2
    # v2 rejects these outright, so they must never be sent.
    assert "pageSize" not in seen[0].params
    assert "limit" not in seen[0].params

    assert [t.transaction_id for t in transactions] == ["t1", "t2"]
    assert transactions[0].amount == Decimal("-10.5")
    assert transactions[0].transaction_date.isoformat() == "2026-08-02"


def test_item_url_is_built_only_from_the_uuid() -> None:
    item_id = UUID("70642699-1111-4111-8111-111111111111")
    assert _item_url("https://api.pluggy.ai/", item_id) == (
        "https://api.pluggy.ai/items/70642699-1111-4111-8111-111111111111"
    )
    with pytest.raises(ValueError):
        _item_url("https://api.pluggy.ai", "../webhooks")


@pytest.mark.asyncio
async def test_transactions_surface_upstream_failures(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "pluggy-secret-body"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "key"})
        return httpx.Response(
            410,
            json={"code": "ENDPOINT_DEPRECATED", "apiKey": secret},
        )

    client = _live_client(monkeypatch, handler)

    with caplog.at_level(logging.WARNING, logger="app.services.pluggy"):
        with pytest.raises(UpstreamError, match="Pluggy transactions fetch failed") as raised:
            await client.fetch_transactions("acc-1")

    assert secret not in str(raised.value)
    assert "ENDPOINT_DEPRECATED" not in str(raised.value)
    assert secret not in caplog.text
    assert "[redacted]" in caplog.text
    assert "410" in caplog.text

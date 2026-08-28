"""Pluggy HTTP client tests.

Production sync broke because Pluggy retired ``GET /transactions`` in favour of
``GET /v2/transactions`` with cursor pagination. The local simulator hid it: it
never issues a request, so the whole suite passed against a dead endpoint. These
tests pin the wire contract instead of the simulated behaviour.
"""

from collections.abc import Callable
from decimal import Decimal

import httpx
import pytest

from app.core.exceptions import UpstreamError
from app.services.pluggy import PluggyClient


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
    seen_urls: list[str] = []
    seen_cursors: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "key"})

        seen_urls.append(request.url.path)
        seen_cursors.append(request.url.params.get("cursor"))

        if request.url.params.get("cursor") is None:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"id": "t1", "description": "Padaria", "amount": -10.5,
                         "date": "2026-08-02T00:00:00.000Z"}
                    ],
                    "nextCursor": "page-2",
                },
            )
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "t2", "description": "Soldo", "amount": 4200,
                     "date": "2026-08-01T00:00:00.000Z"}
                ],
                "nextCursor": None,
            },
        )

    client = _live_client(monkeypatch, handler)
    transactions = await client.fetch_transactions("acc-1")

    assert seen_urls == ["/v2/transactions", "/v2/transactions"]
    assert seen_cursors == [None, "page-2"]

    assert [t.transaction_id for t in transactions] == ["t1", "t2"]
    assert transactions[0].amount == Decimal("-10.5")
    assert transactions[0].transaction_date.isoformat() == "2026-08-02"


@pytest.mark.asyncio
async def test_transactions_surface_upstream_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "key"})
        return httpx.Response(410, json={"code": "ENDPOINT_DEPRECATED"})

    client = _live_client(monkeypatch, handler)

    with pytest.raises(UpstreamError):
        await client.fetch_transactions("acc-1")

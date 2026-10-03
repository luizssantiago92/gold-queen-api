"""Security headers must ride along with CORS and must not add a CSP."""

import pytest
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from app.core.security_headers import SecurityHeadersMiddleware

PRODUCTION = "https://gold-queen-web.vercel.app"


def test_security_headers_are_present(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert (
        response.headers["strict-transport-security"]
        == "max-age=31536000; includeSubDomains"
    )
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" not in response.headers


def test_security_headers_keep_cors(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": PRODUCTION})
    assert response.headers["access-control-allow-origin"] == PRODUCTION
    assert response.headers["x-frame-options"] == "DENY"


def test_docs_is_served_without_a_content_security_policy(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "content-security-policy" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_non_http_scope_is_unchanged() -> None:
    seen: dict[str, str] = {}

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del receive, send
        seen["type"] = scope["type"]

    await SecurityHeadersMiddleware(app)({"type": "lifespan"}, _receive, _send)
    assert seen["type"] == "lifespan"


@pytest.mark.asyncio
async def test_existing_frame_header_is_not_replaced() -> None:
    sent: list[Message] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del scope, receive
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"x-frame-options", b"SAMEORIGIN")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    async def capture(message: Message) -> None:
        sent.append(message)

    await SecurityHeadersMiddleware(app)({"type": "http"}, _receive, capture)

    headers = sent[0]["headers"]
    frames = [value for name, value in headers if name == b"x-frame-options"]
    assert frames == [b"SAMEORIGIN"]
    assert any(name == b"x-content-type-options" for name, _ in headers)


async def _receive() -> Message:
    return {"type": "http.request"}


async def _send(_message: Message) -> None:
    return None

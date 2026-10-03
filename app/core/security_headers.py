"""Response headers that do not depend on the route.

No Content-Security-Policy: a default policy would block the Swagger UI at
``/docs``. CORS stays on its own middleware.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Browsers ignore Strict-Transport-Security when the response arrives over
# plain HTTP (RFC 6797). Sending it on every response covers the HTTPS host
# on Render and leaves local http://127.0.0.1 usable, with no environment
# branch that a health check could forget.
_SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                present = {name.lower() for name, _ in headers}
                for name, value in _SECURITY_HEADERS:
                    if name not in present:
                        headers.append((name, value))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)

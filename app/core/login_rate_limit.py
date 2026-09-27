"""In-process throttle for password login.

Each call to ``POST /v1/auth/login`` consumes one attempt for the caller,
before the password is hashed, so a burst cannot spend bcrypt on every guess.

Limitation on serverless hosts (Vercel) and on multi-worker processes: the
window lives in this isolate's memory. A cold start resets it, and other
instances do not see it. That blunts credential stuffing against a warm
instance; it is not a global quota. A shared store is intentionally not
introduced — this deployment has no Redis or equivalent.

When ``LOGIN_TRUST_PROXY_HEADERS`` is on (the default), the caller is taken
from ``X-Real-IP`` or the first ``X-Forwarded-For`` hop, which Vercel and
Render set. If the process is reachable directly, a client can rotate those
headers and bypass the window. Keep the app behind the platform proxy.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import LoginRateLimitError

_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def reset_login_rate_limit() -> None:
    """Drop every bucket. Tests use this so cases do not share a window."""
    with _lock:
        _attempts.clear()


def login_client_key(request: Request, *, trust_proxy_headers: bool) -> str:
    if trust_proxy_headers:
        real_ip = request.headers.get("x-real-ip", "").strip()
        if real_ip:
            return real_ip
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def enforce_login_rate_limit(request: Request, *, now: float | None = None) -> None:
    settings = get_settings()
    key = login_client_key(
        request, trust_proxy_headers=settings.login_trust_proxy_headers
    )
    moment = time.monotonic() if now is None else now
    limit = settings.login_rate_limit_max
    window = float(settings.login_rate_limit_window_seconds)
    with _lock:
        bucket = _attempts[key]
        cutoff = moment - window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(bucket[0] + window - moment + 0.999))
            raise LoginRateLimitError(
                "Too many login attempts. Try again shortly.",
                retry_after_seconds=retry_after,
            )
        bucket.append(moment)

"""Guards for the shared public demo account.

Credentials are published in the README and pre-filled in the web login, so
every visitor authenticates as the same user. Writes that would unlink the
sandbox bank, or replace it, are rejected. The daily AI quota is counted per
visitor instead of once for that shared user.
"""

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import DemoReadOnlyError
from app.core.login_rate_limit import login_client_key
from app.models.entities import User
from app.services.demo_refresh import is_demo_email

# IPv6 fits well under this. A longer forwarded value is truncated so a client
# who can set the header cannot store an arbitrarily large quota key.
_SUBJECT_KEY_MAX = 128


def ensure_not_demo(user: User) -> None:
    if is_demo_email(user.email):
        raise DemoReadOnlyError("The public demo account is read-only.")


def demo_quota_subject(user: User, request: Request) -> str:
    """Return "" for a normal user, or the login limiter's client key for a demo.

    The key follows ``LOGIN_TRUST_PROXY_HEADERS``. On Render that header is the
    platform's client address, so a caller-supplied ``X-Real-IP`` does not open
    a fresh bucket. With the flag off, the socket address is used instead.
    """
    if not is_demo_email(user.email):
        return ""
    settings = get_settings()
    key = login_client_key(
        request, trust_proxy_headers=settings.login_trust_proxy_headers
    )
    return key[:_SUBJECT_KEY_MAX]

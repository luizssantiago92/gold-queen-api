"""Password hashing and JWT issuing/verification.

Password hashes are bcrypt ``$2b$`` strings at 12 rounds, the same prefix and
cost passlib's bcrypt scheme wrote. Hashes already stored in production still
verify through ``bcrypt.checkpw``. bcrypt only consumes the first 72 bytes of
a password. bcrypt 5 raises ``ValueError`` instead of truncating, so callers
reject a longer password before hashing and treat it as a mismatch on verify.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

# passlib's bcrypt scheme default, and bcrypt.gensalt()'s default.
BCRYPT_ROUNDS = 12
BCRYPT_MAX_PASSWORD_BYTES = 72

# A real 12-round bcrypt hash used only when the email is not registered.
# Login still rejects that request. The check exists so the missing-user path
# spends the same password verification as a wrong password.
UNKNOWN_EMAIL_BCRYPT_HASH = (
    "$2b$12$i4JenkQrauMKUOM2hJ6iq.55osq9Ve5PPeneBbyChX4B7oAIUFEty"
)


def _password_bytes(plain_password: str) -> bytes:
    encoded = plain_password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password must be at most 72 bytes.")
    return encoded


def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(
        _password_bytes(plain_password),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    )
    return hashed.decode("ascii")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return whether ``plain_password`` matches a stored bcrypt hash.

    A password over 72 bytes, or a hash that is not ASCII bcrypt text, is a
    mismatch. The function does not truncate the password to make it match.
    """
    try:
        password = _password_bytes(plain_password)
        hashed = password_hash.encode("ascii")
    except (UnicodeEncodeError, ValueError):
        return False
    try:
        return bcrypt.checkpw(password, hashed)
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expires_at, "iat": datetime.now(UTC)}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    if isinstance(token, bytes):
        return token.decode("ascii")
    return token


def decode_access_token(token: str) -> str:
    """Return the token subject (user id) or raise AuthenticationError."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    subject = payload.get("sub")
    if not subject:
        raise AuthenticationError("Token is missing a subject.")
    return str(subject)

"""Domain exceptions and the single HTTP error body."""

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

VALIDATION_DETAIL = "Request validation failed"
INTERNAL_DETAIL = "Internal server error"
INTERNAL_CODE = "internal_error"

_STATUS_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthenticated",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "validation_error",
    status.HTTP_429_TOO_MANY_REQUESTS: "too_many_requests",
    status.HTTP_500_INTERNAL_SERVER_ERROR: INTERNAL_CODE,
    status.HTTP_502_BAD_GATEWAY: "bad_gateway",
    status.HTTP_503_SERVICE_UNAVAILABLE: "service_unavailable",
}


class DomainError(Exception):
    """Base class for expected business rule violations."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class AuthenticationError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthenticated"


class ConnectionLimitError(DomainError):
    """Raised when the Free plan bank connection quota is exhausted."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "connection_limit_reached"


class DemoReadOnlyError(DomainError):
    """Raised when the shared public demo account tries to mutate data."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "demo_read_only"


class RegistrationDisabledError(DomainError):
    """Raised when public signup is closed."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "registration_disabled"


class RateLimitError(DomainError):
    """Raised when the daily Gold Queen interaction quota is exhausted."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit_reached"


class LoginRateLimitError(DomainError):
    """Raised when the login attempt window is exhausted.

    Distinct from ``RateLimitError`` so clients do not treat a locked login
    as the Queen's daily AI quota.
    """

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "login_rate_limited"

    def __init__(self, message: str, *, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.headers = {"Retry-After": str(retry_after_seconds)}


class UpstreamError(DomainError):
    """Raised when Pluggy or the AI provider fails."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_error"


def _detail_text(detail: object) -> str:
    """Use a string detail. Structured payloads can carry submitted secrets."""
    if isinstance(detail, str) and detail:
        return detail
    return "Request failed"


def _public_loc(loc: object) -> list[str | int]:
    if not isinstance(loc, (list, tuple)):
        return []
    public: list[str | int] = []
    for part in loc:
        if isinstance(part, str):
            public.append(part)
        elif isinstance(part, int) and not isinstance(part, bool):
            public.append(part)
    return public


def _public_message(error: dict[str, Any]) -> str:
    message = error.get("msg")
    text = message if isinstance(message, str) and message else "Invalid value"
    submitted = error.get("input")
    if isinstance(submitted, str) and submitted and submitted in text:
        return "Invalid value"
    return text


def _public_type(value: object) -> str:
    if isinstance(value, str) and value:
        return value
    return "value_error"


def public_field_errors(errors: Sequence[Any]) -> list[dict[str, object]]:
    """Keep loc, msg, and type. Drop input, ctx, and any other key."""
    return [
        {
            "loc": _public_loc(error.get("loc")),
            "msg": _public_message(error),
            "type": _public_type(error.get("type")),
        }
        for error in errors
        if isinstance(error, dict)
    ]


def _error_response(
    status_code: int,
    content: dict[str, object],
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=dict(headers) if headers else None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return _error_response(
            exc.status_code,
            {"detail": exc.message, "code": exc.code},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {
                "detail": VALIDATION_DETAIL,
                "code": "validation_error",
                "errors": public_field_errors(exc.errors()),
            },
        )

    def _http_exception_response(exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(
            exc.status_code,
            {
                "detail": _detail_text(exc.detail),
                "code": _STATUS_CODES.get(exc.status_code, "http_error"),
            },
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_starlette_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _http_exception_response(exc)

    @app.exception_handler(HTTPException)
    async def handle_fastapi_http_exception(
        _request: Request, exc: HTTPException
    ) -> JSONResponse:
        return _http_exception_response(exc)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("Unhandled application error", exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"detail": INTERNAL_DETAIL, "code": INTERNAL_CODE},
        )

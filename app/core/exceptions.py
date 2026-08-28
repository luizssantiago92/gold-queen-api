"""Domain exceptions and their HTTP representations."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


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


class RateLimitError(DomainError):
    """Raised when the daily Gold Queen interaction quota is exhausted."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit_reached"


class UpstreamError(DomainError):
    """Raised when Pluggy or the AI provider fails."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

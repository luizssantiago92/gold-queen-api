"""Public error body shared by every handled failure."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class FieldError(BaseModel):
    """One invalid location. The value the client sent is not included."""

    loc: list[str | int]
    msg: str
    type: str


class ErrorResponse(BaseModel):
    """Failure body. ``errors`` is present only when validation rejected fields."""

    detail: str
    code: str
    errors: list[FieldError] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "detail": "Missing bearer token.",
                    "code": "unauthenticated",
                },
                {
                    "detail": "Request validation failed",
                    "code": "validation_error",
                    "errors": [
                        {
                            "loc": ["body", "password"],
                            "msg": "String should have at least 8 characters",
                            "type": "string_too_short",
                        }
                    ],
                },
            ]
        }
    )


def error_responses(*items: tuple[int, str]) -> dict[int | str, dict[str, Any]]:
    """OpenAPI responses that all use the shared error schema."""
    return {
        status_code: {"model": ErrorResponse, "description": description}
        for status_code, description in items
    }

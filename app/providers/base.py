from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Completion:
    content: str
    model: str
    provider: str


class ProviderError(Exception):
    """Upstream failure the AI engine can classify as transient or permanent."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        timed_out: bool = False,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.timed_out = timed_out
        self.retry_after_seconds = retry_after_seconds

    @property
    def is_retryable(self) -> bool:
        if self.timed_out:
            return True
        if self.status_code == 429:
            return True
        return self.status_code is not None and self.status_code >= 500


class Provider(Protocol):
    name: str

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> Completion: ...

    def health(self) -> bool: ...

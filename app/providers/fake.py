from __future__ import annotations

from app.providers.base import Completion, ProviderError


class FakeProvider:
    name: str

    def __init__(
        self,
        name: str,
        *,
        content: str = "ok",
        model: str = "fake-model",
        error: ProviderError | None = None,
        healthy: bool = True,
    ) -> None:
        self.name = name
        self.content = content
        self.model = model
        self.error = error
        self.healthy = healthy
        self.calls = 0

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> Completion:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return Completion(content=self.content, model=self.model, provider=self.name)

    def health(self) -> bool:
        return self.healthy

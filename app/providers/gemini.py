from __future__ import annotations

import httpx

from app.providers.base import Completion, ProviderError


def _messages_to_gemini(
    messages: list[dict[str, str]],
) -> tuple[str | None, list[dict]]:
    system_parts: list[str] = []
    contents: list[dict] = []
    for message in messages:
        role = message.get("role", "user")
        text = message.get("content", "")
        if role == "system":
            system_parts.append(text)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": text}]})
    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return system_instruction, contents


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    content = (candidates[0] or {}).get("content") or {}
    parts = content.get("parts") or []
    texts = [str(part.get("text", "")) for part in parts if isinstance(part, dict)]
    return "".join(texts)


class GeminiProvider:
    name = "cloud"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: float = 30,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = client

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> Completion:
        system_instruction, contents = _messages_to_gemini(messages)
        if not contents:
            contents = [{"role": "user", "parts": [{"text": ""}]}]
        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        url = f"{self._base_url}/models/{self._model}:generateContent"
        data = self._request("POST", url, json=payload)
        content = _extract_text(data)
        model = str(data.get("modelVersion", self._model))
        return Completion(content=content, model=model, provider=self.name)

    def health(self) -> bool:
        try:
            self._request("GET", f"{self._base_url}/models/{self._model}")
            return True
        except ProviderError:
            return False

    def _request(self, method: str, url: str, json: dict | None = None) -> dict:
        params = {"key": self._api_key}
        client = self._client or httpx.Client(timeout=self._timeout)
        owns_client = self._client is None
        try:
            response = client.request(method, url, json=json, params=params)
        except httpx.TimeoutException as exc:
            raise ProviderError("gemini timeout", timed_out=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("gemini unreachable", status_code=503) from exc
        finally:
            if owns_client:
                client.close()
        if response.status_code >= 500:
            raise ProviderError("gemini upstream error", status_code=response.status_code)
        if response.status_code >= 400:
            raise ProviderError("gemini client error", status_code=response.status_code)
        return response.json()

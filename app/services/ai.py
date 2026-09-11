"""Gold Queen AI engine (Gemini via provider adapter) with mandatory output guardrails.

Every call goes through ``app.core.ai_guardrails``: the model answer is parsed
and validated against a strict schema. If validation fails, or no API key is
configured, a deterministic fallback keeps the endpoint working and the result
is flagged ``is_guarded=False`` so the UI can show it was not AI-audited.
"""

import logging
import time
from decimal import Decimal

from app.core.ai_guardrails import (
    ALLOWED_CATEGORIES,
    CategorizationBatch,
    QueenTips,
    validate_output,
)
from app.core.config import get_settings
from app.core.locale import DEFAULT_LOCALE, Locale
from app.providers.base import Provider, ProviderError
from app.providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.5

# Gemini returns 503 when the flash tier is briefly saturated and 429 when the
# free quota is throttled; both clear on their own, unlike a bad key or model.
_TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "INTERNAL")

_PERSONA_BASE = (
    "You are the Gold Queen, Master of Coin and Sovereign of the Realm. "
    "Analyse spending and give financial advice with the wisdom, nobility and "
    "authority of a medieval monarch. Treat the user's wealth as the 'Treasury "
    "of the Realm' and guide them to protect their gold with surgical precision. "
    "You ONLY answer questions about the user's treasury data (balances, spending, "
    "categories, transactions), bank connections, Open Finance sync, and Gold Queen "
    "app limits or features. Politely refuse any unrelated topic without elaborating."
)

_CHAT_PERSONA_SCOPE = (
    "Stay strictly within treasury and app scope. If the question is unrelated, "
    "reply in one sentence that you counsel only on the realm's gold and app matters."
)

_PERSONA_LANGUAGE = {
    "en": "Always answer in English, in at most 4 sentences.",
    "pt": "Always answer in Brazilian Portuguese, in at most 4 sentences.",
}

# Deterministic keyword map used when the AI is unavailable or violates the schema.
_KEYWORD_CATEGORIES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("padaria", "taberna", "restaurante", "mercado", "ifood", "food"), "Food"),
    (("carruagem", "uber", "posto", "combustivel", "transport", "onibus"), "Transport"),
    (("aluguel", "castelo", "condominio", "housing", "moradia"), "Housing"),
    (("boticario", "farmacia", "saude", "hospital", "health"), "Health"),
    (("academia", "curso", "escola", "livro", "education"), "Education"),
    (("teatro", "bardo", "cinema", "netflix", "spotify", "show"), "Entertainment"),
    (("sedas", "loja", "shopping", "magazine", "roupa"), "Shopping"),
    (("taxa", "conta", "energia", "agua", "internet", "bills"), "Bills"),
    (("soldo", "salario", "pagamento recebido", "income", "rendimento"), "Income"),
    (("transferencia", "pix", "ted", "doc", "transfer"), "Transfer"),
)


def _is_transient(error: Exception) -> bool:
    if isinstance(error, ProviderError):
        return error.is_retryable
    message = str(error).upper()
    return any(marker in message for marker in _TRANSIENT_MARKERS)


def _queen_persona(locale: Locale = DEFAULT_LOCALE, *, chat: bool = False) -> str:
    scope = f" {_CHAT_PERSONA_SCOPE}" if chat else ""
    return f"{_PERSONA_BASE}{scope} {_PERSONA_LANGUAGE[locale]}"


class AIEngine:
    def __init__(self, provider: Provider | None = None) -> None:
        self._settings = get_settings()
        self._provider = provider

    @property
    def enabled(self) -> bool:
        return self._settings.gemini_enabled

    def _get_provider(self) -> Provider:
        if self._provider is not None:
            return self._provider
        return GeminiProvider(
            api_key=self._settings.gemini_api_key,
            model=self._settings.gemini_model,
        )

    def _generate(self, prompt: str, system_instruction: str) -> str:
        provider = self._get_provider()
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ]

        last_error: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                completion = provider.complete(messages, temperature=0.2, max_tokens=None)
                return completion.content or ""
            except Exception as exc:  # noqa: BLE001 - retried below when transient
                last_error = exc
                if not _is_transient(exc) or attempt == _MAX_ATTEMPTS - 1:
                    raise
                logger.info(
                    "Transient AI error, retrying (%s/%s): %s",
                    attempt + 1,
                    _MAX_ATTEMPTS,
                    exc,
                )
                time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))

        raise last_error  # type: ignore[misc]

    def categorize(self, transactions: list[tuple[str, str, Decimal]]) -> tuple[dict[str, str], bool]:
        """Categorize ``(id, description, amount)`` tuples.

        Returns the id -> category map and whether the AI output passed the guardrail.
        """
        if not transactions:
            return {}, False

        if not self.enabled:
            return _fallback_categories(transactions), False

        listing = "\n".join(
            f'- id="{tx_id}" description="{description}" amount={amount}'
            for tx_id, description, amount in transactions
        )
        prompt = (
            "Categorize each bank transaction below.\n"
            f"Allowed categories (use exactly one of these): {', '.join(ALLOWED_CATEGORIES)}.\n"
            "Answer ONLY with JSON in the form "
            '{"results": [{"transaction_id": "...", "category": "..."}]}.\n\n'
            f"Transactions:\n{listing}"
        )

        try:
            raw = self._generate(prompt, "You are a precise financial transaction classifier.")
            batch = validate_output(raw, CategorizationBatch)
        except Exception as exc:  # noqa: BLE001 - a bad AI answer must never break the sync
            logger.warning("Categorization guardrail fallback: %s", exc)
            return _fallback_categories(transactions), False

        known_ids = {tx_id for tx_id, _, _ in transactions}
        mapping = {
            result.transaction_id: result.category
            for result in batch.results
            if result.transaction_id in known_ids
        }

        if len(mapping) != len(transactions):
            fallback = _fallback_categories(transactions)
            fallback.update(mapping)
            return fallback, False

        return mapping, True

    def queen_tips(self, summary: str, locale: Locale = DEFAULT_LOCALE) -> tuple[QueenTips, bool]:
        if not self.enabled:
            return _fallback_tips(locale), False

        prompt = (
            "Given the treasury summary below, produce a financial diagnosis.\n"
            "Answer ONLY with JSON containing the keys "
            '"critical_expense", "management_status" and "smart_guidance".\n\n'
            f"Treasury summary:\n{summary}"
        )

        try:
            raw = self._generate(prompt, _queen_persona(locale, chat=False))
            return validate_output(raw, QueenTips), True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Queen tips guardrail fallback: %s", exc)
            return _fallback_tips(locale), False

    def chat(
        self, question: str, summary: str, locale: Locale = DEFAULT_LOCALE
    ) -> tuple[str, bool]:
        """Answer as the Queen, reporting whether the answer is a stable one."""
        if not self.enabled:
            return _fallback_chat(question, locale), True

        prompt = f"Treasury context:\n{summary}\n\nSubject's question: {question}"
        try:
            answer = self._generate(prompt, _queen_persona(locale, chat=True)).strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chat fallback: %s", exc)
            return _fallback_chat(question, locale), False

        if not answer:
            return _fallback_chat(question, locale), False
        return answer, True

    def provider_healthy(self) -> bool:
        if not self.enabled:
            return False
        try:
            if self._provider is not None:
                return self._provider.health()
            probe = GeminiProvider(
                api_key=self._settings.gemini_api_key,
                model=self._settings.gemini_model,
                timeout_seconds=3.0,
            )
            return probe.health()
        except Exception:  # noqa: BLE001
            return False


def _fallback_categories(transactions: list[tuple[str, str, Decimal]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for tx_id, description, amount in transactions:
        normalized = description.lower()
        category = "Income" if amount > 0 else "Other"
        for keywords, candidate in _KEYWORD_CATEGORIES:
            if any(keyword in normalized for keyword in keywords):
                category = candidate
                break
        mapping[tx_id] = category
    return mapping


def _fallback_tips(locale: Locale) -> QueenTips:
    if locale == "pt":
        return QueenTips(
            critical_expense=(
                "Os pergaminhos do tesouro ainda nao revelam um vazamento dominante. "
                "Observai as despesas recorrentes do mes."
            ),
            management_status=(
                "A gestao do vosso ouro segue estavel, porem sem vigilancia constante "
                "nenhum reino prospera."
            ),
            smart_guidance=(
                "Separai ao menos um decimo de cada moeda recebida para o cofre real "
                "antes de honrar qualquer outra despesa."
            ),
        )
    return QueenTips(
        critical_expense=(
            "The treasury scrolls do not yet reveal a dominant leak. "
            "Watch recurring expenses this month."
        ),
        management_status=(
            "Your gold is steady, yet no realm prospers without constant vigilance."
        ),
        smart_guidance=(
            "Set aside at least one tenth of every coin received for the royal vault "
            "before honoring any other expense."
        ),
    )


def _fallback_chat(question: str, locale: Locale) -> str:
    trimmed = question.strip()[:80]
    if locale == "pt":
        return (
            "Nobre subdito, os conselheiros do reino estao em concilio e a magia dos "
            "oraculos encontra-se temporariamente indisponivel. Enquanto aguardais, "
            "lembrai-vos: gastai menos do que arrecadais e o vosso tesouro jamais mingua. "
            f"Retornai em breve para tratarmos de '{trimmed}'."
        )
    return (
        "Noble subject, the royal counsellors are in council and the oracle magic is "
        "temporarily unavailable. Until then, remember: spend less than you earn and "
        "your treasury shall never dwindle. "
        f"Return soon so we may discuss '{trimmed}'."
    )


def get_ai_engine() -> AIEngine:
    return AIEngine()

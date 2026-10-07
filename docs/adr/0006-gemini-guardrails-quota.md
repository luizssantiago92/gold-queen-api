# ADR 0006: Gemini categorization with guardrails, a rule fallback, and a daily quota

- Status: Accepted
- Recorded: 2026-10-07 (the service already runs this way)

## Context

Sync needs a category for each new transaction. Queen's Tips and chat need a short diagnosis grounded in that user's balances. The historical brief named `gemini-1.5-flash` and an in-memory cache of 10 interactions a day. `app/core/config.py` records that 1.5-flash is retired, that 2.5-flash is closed to new API keys, and that the free tier caps the whole project at 20 generations a day, shared with tips and categorization. The demo still has to answer when no key is configured.

## Decision

The client is `httpx` against `generativelanguage.googleapis.com` (`app/providers/gemini.py`). The default model is `gemini-3.6-flash`. The API key is sent in the `x-goog-api-key` header. Temperature is 0.2. Transient HTTP 429 and 5xx responses retry up to three times, honoring `Retry-After` up to 8 seconds.

Every categorization and tips response is parsed as JSON and validated in `app/core/ai_guardrails.py`. Categories must be one of eleven names. Tips must be three non-empty strings within the field caps. Anything else, including a missing `GEMINI_API_KEY`, uses the keyword map or the fixed text. Categorization and Queen's Tips then set `is_guarded` false. Chat has no `is_guarded` field; a missing key still returns the fixed reply and may cache it, while a failed call is not cached. A categorization batch that does not name every transaction id is treated as unguarded and the gaps are filled from the keyword map.

Chat and Queen's Tips share `CHAT_DAILY_LIMIT` (default 5). The counter is an upsert guarded by a unique constraint, in `chat_usage` or, for the demo, `demo_chat_usage`. A same-day chat cache hit and an unchanged tips summary do not consume a unit. Off-topic chat is refused before the quota and before Gemini. A failed chat completion is not cached and the unit is refunded. Tips that fail the guardrail are not cached.

## Consequences

The model cannot invent a category name that reaches the database as a guarded row. Fallback copy is deterministic and bilingual (`en` / `pt`). A higher `CHAT_DAILY_LIMIT` would promise calls the free tier cannot serve. The cache stores the question text, which is called out in the privacy requirement.

## Alternatives

The `google-genai` SDK from the historical brief is not a dependency; the provider interface in `app/providers/` wraps `httpx`, with a fake provider for tests. An in-memory `lru_cache` would reset on every Render cold start and would not be shared across workers. Skipping the guardrail and storing the raw model string would let an unknown category through.

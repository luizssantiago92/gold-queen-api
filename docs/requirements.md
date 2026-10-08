# Requirements

This is the current behavior of Gold Queen API. The original brief in [history/PRD.md](history/PRD.md) is historical. Where an identifier below matches that brief (RF01–RF05), the requirement is the implementation, including the deltas in the next section.

## Deltas from the historical brief

The running service differs from `docs/history/PRD.md` in ways the code already settled:

- The shared daily AI quota is `CHAT_DAILY_LIMIT` (default **5**), not 10. Chat and Queen's Tips draw from the same counter.
- The same-day cache is the `chat_cache` table, not an in-memory `lru_cache`.
- Pluggy is called at `/v2/transactions` through `httpx`. With no credentials, sync uses the offline simulator in `app/services/pluggy.py`.
- The model is `gemini-3.6-flash`, called with `httpx` (`app/providers/gemini.py`). The historical `google-genai` SDK and `gemini-1.5-flash` are not in the dependency list.
- There is no `Cards` table and no `InvestmentAdvice` table. The README roadmap says the same thing.

## Functional requirements

### RF01 — Bank connections

A signed-in user can list linked banks, obtain a Pluggy connect token, sync an item, and unlink a bank.

- `GET /v1/connections` returns that user's rows only.
- `POST /v1/connections/connect` refuses a new token once the user has `MAX_BANK_CONNECTIONS` banks (default 3) with `403` / `connection_limit_reached`.
- `POST /v1/connections/sync` inserts a transaction when its `pluggy_transaction_id` is new for that account and the movement is new too. The movement key is account, description, amount in cents, and date. A later fetch that mints a new Pluggy id for that key is skipped, including copies inside the same fetch. Two legitimate purchases with the same description, cent amount, and day collapse into one row. The same Pluggy id still updates description, amount, and date. A repeat sync still updates balances and `last_synced_at`. A live item can be claimed on first sync only when Pluggy's `clientUserId` matches the user id. The offline simulator has no tenant, so it skips that check. An item already stored for someone else returns `404`, the same response as a missing connection.
- `DELETE /v1/connections/{id}` removes that user's transactions, then accounts, then the connection, which frees a slot in the limit.
- The public demo accounts receive `403` / `demo_read_only` on connect, sync, and delete (RF07).

Trace: `app/routers/connections.py`, `app/services/sync.py`, `tests/test_connections.py`.

### RF02 — Categorization with guardrails

New transactions from a sync are categorized before they are stored.

- The model may return only the closed vocabulary in `ALLOWED_CATEGORIES` (`Food`, `Transport`, `Housing`, `Health`, `Education`, `Entertainment`, `Shopping`, `Bills`, `Income`, `Transfer`, `Other`).
- Output is parsed as JSON and validated by `CategorizationBatch`. A markdown fence around the JSON is accepted. An unknown category, malformed JSON, or a batch that does not cover every id is rejected.
- A rejected or missing model result uses the keyword map in `app/services/ai.py`. Those rows store `is_guarded` false. A fully accepted batch stores `is_guarded` true.
- With no `GEMINI_API_KEY`, categorization is the keyword map and `is_guarded` is false. Sync still completes.

Trace: `app/core/ai_guardrails.py`, `app/services/ai.py`, `app/services/sync.py`, `tests/test_guardrails.py`, `tests/test_ai.py`.

### RF03 — Dashboard

Dashboard routes read PostgreSQL. They do not call Pluggy. Amounts are `Decimal` values serialized as strings with two decimal places. Dates are `YYYY-MM-DD`. Every route requires a bearer token and returns only the caller's rows.

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/v1/dashboard/overview` | Total balance, each bank's balance and share, month income and expenses, `reference_month` |
| `GET` | `/v1/dashboard/categories` | Current-month expenses grouped by display category |
| `GET` | `/v1/dashboard/monthly-series` | Cumulative expenses for each elapsed day of the month |
| `GET` | `/v1/dashboard/transactions` | Current month, newest first, `page` (default 1) and `limit` (default 20, max 100), SQL `OFFSET`/`LIMIT` and `COUNT` |
| `GET` | `/v1/dashboard/transactions/{id}` | One row, or `404` when it is not the caller's |

`display_category` is computed at read time from the description and account type (`app/services/display_category.py`). It is not a column. The stored `category` remains the closed vocabulary from RF02. An empty treasury returns zero totals.

Trace: `app/routers/dashboard.py`, `app/services/treasury.py`, `tests/test_dashboard.py`, `tests/test_display_category.py`.

### RF04 — Queen's Tips

`GET /v1/advisor/queen-tips` returns `critical_expense`, `management_status`, and `smart_guidance` for the signed-in treasury.

- The prompt is grounded with `treasury.build_ai_summary()`, which includes balances and the bank and chat limits.
- The answer must validate as `QueenTips` (non-empty strings within the field length caps). Failure, or no API key, returns the fixed fallback and `is_guarded` false. A fallback is not cached.
- A same-day cache hit is keyed by the hash of `queen-tips:` plus the summary, so a new sync changes the key. A hit spends no model call and no daily quota. The stored payload is JSON. A legacy row that is not valid JSON is a miss.
- Language is the `locale` query when set (`en` or `pt`). Otherwise `Accept-Language` is used. Portuguese (`pt…`) selects `pt`; anything else, including a missing header, selects `en`.
- The call shares RF05's daily quota. Demo visitors are counted per client address.

Trace: `app/routers/advisor.py`, `app/services/ai.py`, `app/core/locale.py`, `tests/test_advisor_and_chat.py`, `tests/test_openapi.py`.

### RF05 — Chat and the shared daily quota

`POST /v1/chat/query` answers one question and returns `remaining_requests` and `daily_limit`.

- The body is `question` (3–500 characters) and `locale` (`en` or `pt`, default `en`). An off-topic question gets a fixed refusal in that language and does not consume quota or call Gemini. A question is in scope when it matches the treasury and app vocabulary in `app/services/chat_scope.py`. The comparison casefolds the question and the vocabulary and strips accents with NFKD, so `transações` matches `transac` and `mês` matches `mes`.
- An in-scope question is normalized (lowercase, collapsed whitespace) and hashed. The same hash for the same user on the same `usage_date` is served from `chat_cache` and does not consume quota.
- Otherwise the request consumes one unit of `CHAT_DAILY_LIMIT` (default 5) and then calls the model with the treasury summary and the Queen persona. The prompt asks for at most four sentences and tells the model to stay on treasury and app topics. The code does not truncate a longer answer.
- A model failure is not cached. The consumed unit is refunded. A missing API key uses the rule fallback and is treated as a stable answer (it can be cached).
- Exhausting the quota returns `429` / `rate_limit_reached` with the themed English or Portuguese message. That code is distinct from login throttling (`login_rate_limited`).
- Consumption is one upsert. On PostgreSQL and SQLite the unique key stops two concurrent requests from both passing the limit. A normal user counts on `(user_id, usage_date)`. A demo user counts on `(user_id, subject_key, usage_date)`.

Trace: `app/routers/chat.py`, `app/services/rate_limit.py`, `app/services/chat_scope.py`, `tests/test_advisor_and_chat.py`, `tests/test_chat_scope.py`, `tests/test_rate_limit.py`.

### RF06 — Accounts and bearer tokens

- `POST /v1/auth/register` creates a user and returns `201` without the password hash. Email must be unique (`409` / `conflict`). Display name is 2–80 characters. Password is at least 8 characters and at most 72 UTF-8 bytes (`422` when longer). The hash is bcrypt `$2b$`, 12 rounds.
- Public signup follows `ALLOW_REGISTRATION`. When the variable is unset, signup is open in development and closed when `ENVIRONMENT=production`. `render.yaml` sets `ALLOW_REGISTRATION` to `false`. Closed signup returns `403` / `registration_disabled`. Login of an existing user still works.
- `POST /v1/auth/login` returns a bearer JWT (`sub` is the user id, `HS256`, `exp` and `iat`). `JWT_EXPIRE_MINUTES` defaults to 1440. The body is `access_token`, `token_type` (`bearer`), and `expires_in_minutes`. Unknown email and wrong password both return `401` / `unauthenticated` with the same message. An unknown email still runs `bcrypt.checkpw` against a fixed dummy hash.
- `GET /v1/auth/me`, and every other `/v1` route except register and login, requires `Authorization: Bearer`. A missing, tampered, expired, or subject-less token is `401`. A token whose user row is gone is `401`.
- `ENVIRONMENT=production` refuses to boot when `JWT_SECRET` is the placeholder or shorter than 32 characters. The error text does not include the secret.

Trace: `app/routers/auth.py`, `app/core/security.py`, `app/core/config.py`, `app/api/deps.py`, `tests/test_auth.py`, `tests/test_password.py`, `tests/test_config.py`.

### RF07 — Public demo

`python -m app.seed` creates `queen@goldqueen.dev` and `squire@goldqueen.dev` when they are absent. The passwords are published in the README because the demo is meant to be tried.

- Connect, sync, and delete return `403` / `demo_read_only`. Reads, Queen's Tips, and chat stay available.
- That user's AI quota is counted per client address (the same key as the login throttle, truncated to 128 characters), so visitors do not share one bucket. A normal account still has one bucket.
- A successful demo login slides transaction dates forward when the newest row is older than yesterday, so the current month still has data. Dashboard reads do not write.

Trace: `app/seed.py`, `app/services/demo_access.py`, `app/services/demo_refresh.py`, `tests/test_demo_access.py`, `tests/test_demo_refresh.py`.

### RF08 — Liveness

- `GET /health` returns `status`, `pluggy_live`, and `ai_live` from local configuration. It does not call Gemini or the database. Render's health check uses this path.
- `GET /health?db=1` runs `SELECT 1`. Success adds `"database":"ok"`. A database error returns `503` with `status` `degraded` and `"database":"unreachable"`.
- `GET /health?deep=1` is the only Gemini probe. It adds `ai_provider`: `ok`, `degraded` (key set, probe failed), or `offline` (no key). The probe timeout is 3 seconds.
- `GET /` redirects to `/docs` with `307` and is omitted from the OpenAPI schema.

Trace: `app/main.py`, `tests/test_advisor_and_chat.py` (health cases).

### RF09 — Error and OpenAPI contract

Handled failures return `{ "detail": string, "code": string }`. A `422` also returns `errors` with `loc`, `msg`, and `type` only. Submitted values are not echoed. An unexpected exception is `500` / `internal_error` with the text "Internal server error" and no traceback in the body. `401` keeps `WWW-Authenticate` when it was already set. Login throttling keeps `Retry-After`.

`info.version` in `/openapi.json` is the `version` field of `pyproject.toml` (`1.0.0`). Routes are tagged `auth`, `connections`, `dashboard`, `advisor`, `chat`, and `health`.

Trace: `app/core/exceptions.py`, `app/main.py`, `tests/test_errors.py`, `tests/test_openapi.py`.

## Non-functional requirements

### RNF01 — Security

- Passwords are stored as bcrypt hashes. Registration and login validation responses omit the submitted password (`tests/test_errors.py`, `tests/test_password.py`).
- Production startup rejects a default or short `JWT_SECRET` (`tests/test_config.py`).
- Login is throttled in process memory: `LOGIN_RATE_LIMIT_MAX` attempts (default 10) per `LOGIN_RATE_LIMIT_WINDOW_SECONDS` (default 60), before bcrypt runs. The counter is not shared across instances and resets on process start. With `LOGIN_TRUST_PROXY_HEADERS` (default true) the key is `X-Real-IP` or the first `X-Forwarded-For` hop. That matches Render. A process exposed directly can be bypassed by rotating those headers (`app/core/login_rate_limit.py`, `tests/test_auth.py`).
- Every HTTP response sets `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, and `Strict-Transport-Security: max-age=31536000; includeSubDomains`. There is no `Content-Security-Policy`, so Swagger UI at `/docs` still loads (`app/core/security_headers.py`, `tests/test_security_headers.py`).
- CORS allows the configured exact origins and, unless `CORS_ORIGIN_REGEX` is empty, preview hosts that end with the Vercel team slug. A `gold-queen-web-*` pattern without the slug is not the default (`app/core/config.py`, `tests/test_cors.py`, `tests/test_config.py`).
- Pluggy error bodies written to logs are redacted for keys, secrets, and bearer tokens (`app/services/pluggy.py`, `tests/test_connections.py`).
- Queries for connections, accounts, and transactions are filtered by the token's user id.
- CI runs `pip-audit` on `requirements-dev.txt`. CodeQL analyzes Python and GitHub Actions. Dependabot opens weekly updates for pip and actions. Workflow permissions start at `contents: read`. The CodeQL job also has `security-events: write` and `actions: read`. The Retornatus job also has `pull-requests: write` for the verdict comment.

### RNF02 — Performance and cold start

- The Render free service sleeps after 15 minutes without traffic and takes about 50 seconds to wake (`docs/deployment.md`, `render.yaml` `plan: free`). The keep-alive job allows for that with `--retry 5 --retry-delay 20 --max-time 120`.
- `GET /health` does not touch Postgres or Gemini, so Render's frequent probe stays cheap. Database and provider checks are opt-in.
- Connect and sync are synchronous handlers, so database work and Gemini categorization run in FastAPI's threadpool. Pluggy HTTP is scheduled back onto the event loop (`tests/test_connections.py`).
- Gemini `generateContent` uses a 30 second timeout. Transient HTTP 429 and 5xx responses retry up to three attempts. `Retry-After` replaces the backoff and is capped at 8 seconds (`app/services/ai.py`, `tests/test_ai.py`).
- Repeat chat questions and an unchanged Queen's Tips summary are served from Postgres and skip the model.

### RNF03 — Availability

- The process stays up when Gemini or Pluggy credentials are absent: categorization, tips, and chat use rule fallbacks, and sync uses the offline simulator.
- A failed chat completion refunds the daily unit so an outage does not spend the quota (`tests/test_advisor_and_chat.py`).
- `GET /health?db=1` reports an unreachable database as `503` instead of crashing the probe.
- `.github/workflows/keep-alive.yml` calls `GET /health?db=1` on Monday and Thursday so the free Supabase project sees activity. The workflow fails unless the body contains `"database":"ok"`.
- Render does not run Alembic. A Postgres schema change is applied with `alembic upgrade head` before or with the deploy that needs it (`docs/deployment.md`).

### RNF04 — Privacy and LGPD-minded handling

This is a description of the data handling in the code, not a legal compliance claim.

- The API stores account email, display name, a password hash, institution names, balances, and transaction descriptions and amounts, plus chat questions and answers for the cache. Access to treasury rows is scoped to the user id in the JWT.
- The browser is not given `DATABASE_URL`, `JWT_SECRET`, `PLUGGY_CLIENT_SECRET`, or `GEMINI_API_KEY`. The web app is a separate repository and talks to this HTTP API.
- Validation errors drop `input` and `ctx`. Upstream Pluggy bodies are redacted before logging. An unexpected error is logged with `logger.error` and the client receives a fixed message.
- Production signup is closed unless `ALLOW_REGISTRATION` is set true. The two demo accounts and their passwords are published on purpose; their bank writes are blocked (RF07).
- There is no endpoint to export or delete a user account, and no job that purges `chat_cache`. Row-level security on the Supabase project is described in [data-model.md](data-model.md): the API connects as the table owner, which bypasses RLS.

Trace: `app/core/exceptions.py`, `app/services/pluggy.py`, `app/models/entities.py`, `docs/deployment.md`.

### RNF05 — Observability

- Operators use `GET /health`, `?db=1`, and `?deep=1` (RF08). The body does not include `ENVIRONMENT`.
- The process logs unexpected exceptions, AI guardrail fallbacks, rejected syncs of someone else's item, and redacted Pluggy failures. It does not emit metrics, traces, or request ids.
- CI prints pytest branch coverage and fails under 85 (`pyproject.toml`). There is no hosted coverage badge.

### RNF06 — Cost

- `render.yaml` pins the free web plan. The Supabase project documented in `docs/deployment.md` is the free plan.
- `CHAT_DAILY_LIMIT` defaults to 5 because the Gemini free tier, as noted in `app/core/config.py`, caps the project well below an unbounded chat. Queen's Tips share that budget. Cache hits and off-topic refusals do not spend it. Categorization runs only for transactions that are not already stored.
- The login throttle and the absence of Redis are deliberate: the deployment has no shared cache (`app/core/login_rate_limit.py`).

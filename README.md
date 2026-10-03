# Gold Queen API

**Gold Queen** is a portfolio-grade Open Finance backend: it aggregates bank accounts through Pluggy, categorizes transactions with guardrailed AI, and powers a medieval-themed financial advisor ("the Gold Queen") that answers user questions with grounded, schema-validated responses.

This repository is the **data and intelligence layer** of the product. The companion frontend lives at [gold-queen-web](https://github.com/luizssantiago92/gold-queen-web).

| Live | URL |
| --- | --- |
| API docs | https://gold-queen-api.onrender.com/docs |
| Web app | https://gold-queen-web.vercel.app |
| OpenAPI | https://gold-queen-api.onrender.com/openapi.json |

## Product positioning

Gold Queen targets users who want a **single view of their money** without spreadsheets:

1. **Open Finance aggregation** — link up to three banks (free tier) via Pluggy and see consolidated balance and monthly cash flow.
2. **Automated categorization** — every synced transaction is classified by Gemini with a closed vocabulary fallback; invalid model output is rejected and flagged `is_guarded: false`.
3. **Display categories** — a second mapping layer turns raw AI labels into portfolio-friendly buckets (subscriptions, bills, credit card, auto debit, etc.) for dashboard charts.
4. **Queen's Tips** — a structured daily diagnosis (critical spending, treasury management, smart guidance) cached per user per day.
5. **Chat with the Queen** — conversational Q&A grounded in the user's real treasury snapshot, with daily rate limits and same-day question cache.

The public demo uses **Pluggy Sandbox** data and intentional UI limits (one pre-linked bank, no live Connect widget). Production-shaped code paths remain available for real Pluggy credentials.

## Stack

| Layer | Technology |
| --- | --- |
| Runtime | Python 3.11+ |
| API | FastAPI (async) |
| ORM | SQLModel (SQLAlchemy + Pydantic v2) |
| Database | PostgreSQL (Supabase in prod) / SQLite (local tests) |
| Migrations | Alembic |
| Open Finance | Pluggy API (`/v2/transactions`) |
| AI | Gemini REST API via httpx (`gemini-3.6-flash`, provider adapter) |
| Auth | JWT (PyJWT + bcrypt) |
| Quality | pytest, ruff, GitHub Actions |

## Quick start

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env        # Windows: copy .env.example .env

# Optional: local PostgreSQL
docker compose up -d
alembic upgrade head

# Demo users (queen@ / squire@)
python -m app.seed

uvicorn app.main:app --reload
```

Interactive docs: http://127.0.0.1:8000/docs

### Demo credentials

| Email | Password |
| --- | --- |
| `queen@goldqueen.dev` | `QueenDemo123!` |
| `squire@goldqueen.dev` | `SquireDemo123!` |

The public demo is **read-only**. Those accounts can sign in and read the dashboard, tips, and chat. `POST /v1/connections/connect`, `POST /v1/connections/sync`, and `DELETE /v1/connections/{id}` return `403` / `demo_read_only`. The daily AI quota for each demo account is counted **per visitor IP** (same `CHAT_DAILY_LIMIT`), using the same client address as the login limiter.

`python -m app.seed` creates users only. `scripts/seed_demo_connection.py` links a sandbox bank by calling connect and sync as the demo user, so it cannot refresh a deploy where that guard is on. See [docs/demo-operations.md](docs/demo-operations.md).

### Offline mode

Without `PLUGGY_CLIENT_ID` / `PLUGGY_CLIENT_SECRET`, Open Finance falls back to a deterministic sandbox simulator. Without `GEMINI_API_KEY`, categorization and advice use rule-based fallbacks. Both paths set `is_guarded: false` so the UI can show unaudited data.

## Configuration

All settings come from environment variables (see [.env.example](.env.example)):

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | PostgreSQL DSN. Falls back to local SQLite when unset. |
| `ENVIRONMENT` | `development` (default) or `production`. Production refuses to start when `JWT_SECRET` is the placeholder or shorter than 32 characters. |
| `JWT_SECRET` | HMAC key for access tokens. Any value is accepted in development, including the placeholder in `.env.example`. In production use a unique random string of at least 32 characters. |
| `PLUGGY_CLIENT_ID` / `PLUGGY_CLIENT_SECRET` | Pluggy application credentials ([dashboard.pluggy.ai](https://dashboard.pluggy.ai)). |
| `GEMINI_API_KEY` | Google AI Studio key ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)). |
| `GEMINI_MODEL` | Defaults to `gemini-3.6-flash`. |
| `CORS_ORIGINS` | Comma-separated exact origins. The default lists local dev plus `https://gold-queen-web.vercel.app` and `https://gold-queen-web-<team>.vercel.app`. |
| `VERCEL_TEAM_SLUG` | Vercel team slug that owns the web app (default `luizssantiago92`). Preview CORS is built from this when `CORS_ORIGIN_REGEX` is unset. |
| `CORS_ORIGIN_REGEX` | Optional override for preview origins. Leave unset to allow only `gold-queen-web` previews whose hostname ends with `-<VERCEL_TEAM_SLUG>.vercel.app`. Set an empty value to disable previews. Do not use a `gold-queen-web-*` pattern without the team slug: anyone can register that project name. |
| `LOGIN_RATE_LIMIT_MAX` | Login attempts allowed per caller per window (default `10`). |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | Length of that window in seconds (default `60`). |
| `LOGIN_TRUST_PROXY_HEADERS` | When `true` (default), the login limiter reads `X-Real-IP` or the first `X-Forwarded-For` hop. |
| `MAX_BANK_CONNECTIONS` | Free-plan bank quota (default `3`). |
| `CHAT_DAILY_LIMIT` | Shared daily AI quota for chat **and** Queen's Tips (default `5`). Demo accounts split this same limit per visitor IP. |
| `ALLOW_REGISTRATION` | Public signup. When unset, enabled in development and test, disabled when `ENVIRONMENT=production`. Set `true` or `false` to override. Closed signup makes `POST /v1/auth/register` return `403` / `registration_disabled`. |

`POST /v1/auth/login` returns `429` / `login_rate_limited` after `LOGIN_RATE_LIMIT_MAX` attempts from the same caller inside the window. The counter is stored in the process that handled the request. On Vercel (and any other serverless or multi-worker host) each isolate has its own counter, a cold start clears it, and instances do not share attempts. The limit slows guessing against one warm instance; it is not an account-wide or fleet-wide lockout. It also trusts proxy IP headers only because the platform overwrites them — do not expose the process directly, or a client can rotate `X-Forwarded-For` and skip the window. There is no Redis (or other shared store) behind this limiter.

Never expose `PLUGGY_CLIENT_SECRET` or `GEMINI_API_KEY` to the browser.

## API surface

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Redirects to `/docs` (307). Not listed in the OpenAPI schema. |
| `GET` | `/health` | Local liveness: `status`, `pluggy_live`, `ai_live`. No outbound calls and no `environment`. `?db=1` runs `SELECT 1` and adds `"database":"ok"` (503 if the database is unreachable). `?deep=1` is the only Gemini probe and adds `ai_provider` (`ok`, `degraded`, or `offline`). |
| `POST` | `/v1/auth/register` | Create account. The password must be 8 to 72 UTF-8 bytes; a longer password returns 422. |
| `POST` | `/v1/auth/login` | JWT bearer token |
| `GET` | `/v1/auth/me` | Current user |
| `GET` | `/v1/connections` | Linked banks |
| `POST` | `/v1/connections/connect` | Pluggy Connect token (3-bank quota) |
| `POST` | `/v1/connections/sync` | Sync accounts + categorize transactions |
| `DELETE` | `/v1/connections/{id}` | Unlink bank and delete its data |
| `GET` | `/v1/dashboard/overview` | Balance, banks, monthly income/expenses |
| `GET` | `/v1/dashboard/categories` | Current-month spending by display category |
| `GET` | `/v1/dashboard/monthly-series` | Cumulative daily spending (month to date) |
| `GET` | `/v1/dashboard/transactions` | Paginated feed (current month) |
| `GET` | `/v1/dashboard/transactions/{id}` | Transaction detail |
| `GET` | `/v1/advisor/queen-tips` | Structured financial diagnosis |
| `POST` | `/v1/chat/query` | Ask the Gold Queen (cached, rate limited) |

`gold-queen-web` does not read `/health`. Render's health check stays on `/health` (no `?db=1` and no `?deep=1`). The keep-alive workflow is the caller that sends `?db=1`.

Every response also sends `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, and `Strict-Transport-Security: max-age=31536000; includeSubDomains`. HSTS is always sent: browsers ignore that header on plain HTTP, so local `http://127.0.0.1` stays usable and the HTTPS host on Render is covered without an environment switch. There is no `Content-Security-Policy`, so `/docs` (Swagger UI) keeps working. CORS is unchanged and still allows only the configured web origins, including `https://gold-queen-web.vercel.app`.

`POST /v1/connections/connect` and `POST /v1/connections/sync` are synchronous handlers. FastAPI runs them in a worker thread, so the SQLAlchemy session and Gemini's blocking client (30s timeout, `time.sleep` on retries) do not stall the process event loop. Pluggy calls stay async and are scheduled back onto that loop.

Full contracts: [docs/frontend-integration.md](docs/frontend-integration.md) · Architecture: [docs/architecture.md](docs/architecture.md)

## Business rules

- **Bank quota:** max 3 connections on the free plan → `403` / `connection_limit_reached`.
- **Daily AI quota:** `CHAT_DAILY_LIMIT` (default 5) shared by **chat and Queen's Tips** → `429` / `rate_limit_reached`. A normal account has one counter. Each demo account (`queen@`, `squire@`) has one counter per client IP.
- **Same-day cache:** identical chat questions return cached answers without consuming quota.
- **Demo is read-only:** connect, sync, and delete on a demo account → `403` / `demo_read_only`. Reads, tips, and chat keep working.
- **Demo date refresh:** demo accounts (`queen@`, `squire@`) auto-shift transaction dates to the current month on dashboard reads.
- **Public signup:** `ALLOW_REGISTRATION` unset is open outside production and closed when `ENVIRONMENT=production`. Closed → `403` / `registration_disabled`.

## AI guardrails

Model output is never trusted directly. [`app/core/ai_guardrails.py`](app/core/ai_guardrails.py):

1. Extracts JSON from the raw response (tolerating markdown fences).
2. Validates against a strict Pydantic schema.
3. Rejects categories outside a closed vocabulary.

On failure, a deterministic fallback is used and affected records carry `is_guarded: false`.

## Documentation

| Document | Contents |
| --- | --- |
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/architecture.md](docs/architecture.md) | System design and data flow |
| [docs/frontend-integration.md](docs/frontend-integration.md) | JSON contracts for the web app |
| [docs/deployment.md](docs/deployment.md) | Supabase + Render + Vercel |
| [docs/demo-operations.md](docs/demo-operations.md) | Seeding and keeping the demo alive |

## Tests

```bash
pytest
ruff check app tests
pip-audit -r requirements-dev.txt
```

CI runs on every push to `main` (`.github/workflows/ci.yml`) and fails if `pip-audit` reports a known vulnerability in the project requirements. The audit is scoped to those files so packages preinstalled on the runner are not treated as dependencies.

## Developing with agents

This repository is governed by [Retornatus](https://github.com/luizssantiago92/retornatus). The finish line, the proof, and the notes live in `.retornatus/`. Pull requests run the Retornatus check, which posts a verdict comment.

Graphify and rtk are local-only tools. Nothing they produce is committed (`graphify-out/` is gitignored).

> **Note:** Root `PRD.md` is a historical product brief. This README and `docs/` are the authoritative technical reference.

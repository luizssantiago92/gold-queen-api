# Gold Queen API

**Gold Queen** is a portfolio-grade Open Finance backend: it aggregates bank accounts through Pluggy, categorizes transactions with guardrailed AI, and powers a medieval-themed financial advisor ("the Gold Queen") that answers user questions with grounded, schema-validated responses.

This repository is the **data and intelligence layer** of the product. The companion frontend lives at [gold-queen-web](https://github.com/luizssantiago92/gold-queen-web).

| Live | URL |
| --- | --- |
| API | https://gold-queen-api.onrender.com |
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
| AI | Google GenAI SDK (`gemini-3.6-flash`) |
| Auth | JWT (python-jose + bcrypt) |
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

`python -m app.seed` creates users only. To populate bank data on a remote deploy, run `python -m scripts.seed_demo_connection` (requires Pluggy credentials). See [docs/demo-operations.md](docs/demo-operations.md).

### Offline mode

Without `PLUGGY_CLIENT_ID` / `PLUGGY_CLIENT_SECRET`, Open Finance falls back to a deterministic sandbox simulator. Without `GEMINI_API_KEY`, categorization and advice use rule-based fallbacks. Both paths set `is_guarded: false` so the UI can show unaudited data.

## Configuration

All settings come from environment variables (see [.env.example](.env.example)):

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | PostgreSQL DSN. Falls back to local SQLite when unset. |
| `JWT_SECRET` | Signing key for access tokens. Use a long random string in production. |
| `PLUGGY_CLIENT_ID` / `PLUGGY_CLIENT_SECRET` | Pluggy application credentials ([dashboard.pluggy.ai](https://dashboard.pluggy.ai)). |
| `GEMINI_API_KEY` | Google AI Studio key ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)). |
| `GEMINI_MODEL` | Defaults to `gemini-3.6-flash`. |
| `CORS_ORIGINS` | Comma-separated allowed origins. |
| `CORS_ORIGIN_REGEX` | Pattern for Vercel preview URLs (default: `gold-queen-web` previews). |
| `MAX_BANK_CONNECTIONS` | Free-plan bank quota (default `3`). |
| `CHAT_DAILY_LIMIT` | Shared daily AI quota for chat **and** Queen's Tips (default `5`). |

Never expose `PLUGGY_CLIENT_SECRET` or `GEMINI_API_KEY` to the browser.

## API surface

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness + `pluggy_live` / `ai_live` flags |
| `POST` | `/v1/auth/register` | Create account |
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

Full contracts: [docs/frontend-integration.md](docs/frontend-integration.md) · Architecture: [docs/architecture.md](docs/architecture.md)

## Business rules

- **Bank quota:** max 3 connections on the free plan → `403` / `connection_limit_reached`.
- **Daily AI quota:** `CHAT_DAILY_LIMIT` (default 5) shared by **chat and Queen's Tips** → `429` / `rate_limit_reached`.
- **Same-day cache:** identical chat questions return cached answers without consuming quota.
- **Demo date refresh:** demo accounts (`queen@`, `squire@`) auto-shift transaction dates to the current month on dashboard reads.

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
```

CI runs on every push to `main` (`.github/workflows/ci.yml`).

## Project process

This repository uses [Spec Guardrails](https://github.com/luizssantiago92/spec-guardrails) for agent workflows (`.specs/`).

```bash
npx @luizsantiago/spec-guardrails doctor
```

> **Note:** Root `PRD.md` is a historical product brief. This README and `docs/` are the authoritative technical reference.

# Gold Queen API

RESTful API for Open Finance data aggregation, automated transaction categorization, and a medieval-themed financial AI advisor using FastAPI, PostgreSQL, and Spec-Guardrails.

The Gold Queen API is the back-end engine that links banks through Open Finance (Pluggy Sandbox), consolidates and categorizes transactions across up to three active bank accounts, validates every AI inference against a strict schema, produces proactive financial education ("Queen's Tips"), and answers user questions through the **Gold Queen** persona under a strict daily usage quota.

## Stack

- Python 3.11+ / FastAPI (async)
- SQLModel (SQLAlchemy + Pydantic v2) / PostgreSQL / Alembic
- Pluggy Sandbox API for Open Finance
- Google GenAI SDK (`gemini-3.6-flash`)
- Runtime AI guardrails (strict Pydantic schema validation)
- JWT authentication (python-jose + passlib/bcrypt)

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

# Create tables and demo users
python -m app.seed

uvicorn app.main:app --reload
```

Interactive docs: <http://127.0.0.1:8000/docs>

### Demo credentials

| Email | Password |
| --- | --- |
| `queen@goldqueen.dev` | `QueenDemo123!` |
| `squire@goldqueen.dev` | `SquireDemo123!` |

### Running without external keys

The API is fully demoable offline. Without `PLUGGY_CLIENT_ID`/`PLUGGY_CLIENT_SECRET` the Open Finance client falls back to a deterministic sandbox simulator, and without `GEMINI_API_KEY` categorization and advice fall back to a rule-based engine. In both cases responses are flagged `is_guarded: false` so the interface can show the data was not AI-audited.

## Configuration

All settings come from environment variables (see [.env.example](.env.example)):

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | PostgreSQL DSN. Falls back to local SQLite when empty. |
| `JWT_SECRET` | Signing key for access tokens. Use a long random string. |
| `PLUGGY_CLIENT_ID` / `PLUGGY_CLIENT_SECRET` | Pluggy application credentials ([dashboard.pluggy.ai](https://dashboard.pluggy.ai)). |
| `GEMINI_API_KEY` | Google AI Studio key ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)). |
| `GEMINI_MODEL` | Defaults to `gemini-3.6-flash`. The PRD named `gemini-1.5-flash`, which Google retired; `gemini-2.5-flash` is likewise closed to new API keys. |
| `CORS_ORIGINS` | Comma-separated origins allowed to call the API. |
| `MAX_BANK_CONNECTIONS` | Free plan bank connection quota (default `3`). |
| `CHAT_DAILY_LIMIT` | Daily Gold Queen interactions per user (default `10`). |

Secrets belong only in the back-end. Never expose `PLUGGY_CLIENT_SECRET` or `GEMINI_API_KEY` to the browser.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/v1/auth/register` | Create an account |
| `POST` | `/v1/auth/login` | Exchange credentials for a JWT |
| `GET` | `/v1/auth/me` | Current user profile |
| `GET` | `/v1/connections` | List linked banks |
| `POST` | `/v1/connections/connect` | Issue a Pluggy Connect token (enforces the 3-bank quota) |
| `POST` | `/v1/connections/sync` | Sync accounts and categorize new transactions |
| `GET` | `/v1/dashboard/overview` | Consolidated treasury, per-bank share, monthly totals |
| `GET` | `/v1/dashboard/categories` | Current-month spending by category |
| `GET` | `/v1/dashboard/transactions` | Paginated unified feed with guardrail status |
| `GET` | `/v1/advisor/queen-tips` | Structured financial diagnosis |
| `POST` | `/v1/chat/query` | Ask the Gold Queen (cached, rate limited) |
| `GET` | `/health` | Liveness and integration status |

Full request/response contract: [docs/frontend-integration.md](docs/frontend-integration.md).

## AI guardrails

Model output is never trusted directly. Every AI response passes through [`app/core/ai_guardrails.py`](app/core/ai_guardrails.py), which:

1. Extracts the JSON payload from the raw response (tolerating markdown fences).
2. Validates it against a strict Pydantic schema.
3. Rejects categories outside a closed vocabulary, so the model cannot invent one.

If validation fails, the request still succeeds using a deterministic fallback, and the affected records carry `is_guarded: false` for visual auditing in the UI.

## Business rules

- **Free plan quota:** a user may link at most 3 banks. Exceeding it returns `403` with code `connection_limit_reached`.
- **Daily AI quota:** 10 interactions per user per day. Exceeding it returns `429` with code `rate_limit_reached` and an in-persona message.
- **Same-day cache:** an identical question on the same day returns the cached answer, consuming neither tokens nor quota.

## Database migrations

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

## Tests

```bash
pytest
ruff check app tests
```

## Project process

This repository uses [Spec Guardrails](https://github.com/luizssantiago92/spec-guardrails) for the agent workflow (`.specs/`).

```bash
npx @luizsantiago/spec-guardrails doctor
```

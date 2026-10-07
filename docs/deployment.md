# Deployment Guide

## Database — Supabase

The project already exists:

| Field | Value |
| --- | --- |
| Name | `gold-queen` |
| Project ref | `ogzmhbjadcoffaneolav` |
| Region | `sa-east-1` (Sao Paulo) |
| API URL | `https://ogzmhbjadcoffaneolav.supabase.co` |
| Plan | Free (USD 0.00 / month) |

Alembic (`alembic/versions`) is the only schema source. Startup calls `SQLModel.metadata.create_all` only when the database is SQLite (local quick-start and tests). Postgres startup does not connect and does not create or alter tables.

**Fresh database.** An empty Postgres, including the one from `docker-compose.yml`, is built with:

```bash
alembic upgrade head
```

Head is `d4e7a2b81c05`. Render starts uvicorn and does not run migrations, so apply them once with `alembic upgrade head` after the deploy that needs them.

**This production database.** It was created by the Supabase migrations `initial_schema` and `enable_row_level_security`, not by Alembic. Do not run `alembic upgrade head` while `alembic_version` is missing: that tries to create tables that already exist.

Revision `c7a1b5e0d942` is already applied by hand: unique constraints `uq_chat_usage_user_date` on `chat_usage (user_id, usage_date)` and `uq_demo_chat_usage_subject_date` on `demo_chat_usage (user_id, subject_key, usage_date)`, and these six columns as `timestamptz`: `users.created_at`, `bank_connections.last_synced_at`, `bank_connections.created_at`, `accounts.updated_at`, `transactions.created_at`, `chat_cache.created_at`.

If `alembic_version` is still missing, record that revision once after confirming the live schema matches it. The command writes `alembic_version` and does not change tables. Do not stamp `head` after `d4e7a2b81c05` exists, or the dedupe revision is skipped:

```bash
alembic stamp c7a1b5e0d942
```

**Revision `d4e7a2b81c05`.** It deletes duplicate `transactions` rows and adds `uq_transactions_account_pluggy_id`. Render does not run Alembic. After merge, with `alembic_version` at `c7a1b5e0d942` (or older, once that revision is stamped), run this once:

```bash
alembic upgrade head
```

**Later schema changes.** Each one is a new Alembic revision, applied with `alembic upgrade head` before or with the deploy. Process startup does not change the Postgres schema.

To point the API at Supabase:

1. Get the database password in **Project Settings → Database**. Use **Reset database password** if it was never stored.
2. Build the connection string using the **Session Pooler** host and the `psycopg2` driver:

```
postgresql+psycopg2://postgres.ogzmhbjadcoffaneolav:<password>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres
```

Two details that differ from what the Supabase dashboard shows by default:

- Supabase prints the URI as `postgresql://`; SQLAlchemy needs the `+psycopg2` suffix.
- The pooler user is `postgres.<project-ref>`, not plain `postgres`.

**Use the pooler, not the direct host.** `db.ogzmhbjadcoffaneolav.supabase.co` publishes only an `AAAA` record, so it is reachable over IPv6 only and fails on IPv4-only networks (most corporate ones). The pooler host resolves to IPv4 `A` records.

On Windows the failure is easy to misread: psycopg2 tries to decode the server error message using the local code page and raises `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe3` instead of the real connection error. If you see that, suspect connectivity, not credentials.

3. Set it as `DATABASE_URL`. On a fresh database, run `alembic upgrade head` first, then create the demo users. On this production database, stamp `c7a1b5e0d942` once if `alembic_version` is missing (see above), then run `alembic upgrade head` so revision `d4e7a2b81c05` deletes duplicate transactions and adds `uq_transactions_account_pluggy_id`. Render does not run that command.

```bash
python -m app.seed
```

### Row Level Security

RLS is already enabled on `users`, `bank_connections`, `accounts`, `transactions`, `chat_cache`, and `chat_usage` by the Supabase migration `enable_row_level_security`. The frontend never talks to Supabase directly. The API connects as the table owner, which bypasses RLS, so no policies are required.

`demo_chat_usage` comes from Alembic, not from that migration. Startup used to enable RLS on it and no longer issues DDL. If that table does not already have RLS, enable it once in the Supabase SQL editor:

```sql
ALTER TABLE public.demo_chat_usage ENABLE ROW LEVEL SECURITY;
```

## API host — Render

The API is a long-lived ASGI service, so a container host fits it better than serverless functions. Vercel is specifically a bad fit here: its Hobby functions time out at 10 seconds, and a Gemini call regularly takes longer than that.

[`render.yaml`](../render.yaml) is a Render blueprint, so the service needs no manual build or start command:

1. In Render, choose **New → Blueprint** and pick this repository.
2. Render reads `render.yaml` and prompts for the secrets marked `sync: false`.
3. Paste `DATABASE_URL`, `PLUGGY_CLIENT_ID`, `PLUGGY_CLIENT_SECRET`, `GEMINI_API_KEY` and `CORS_ORIGINS`. `JWT_SECRET` is generated by Render.
4. After the first deploy, seed the demo users once from **Shell**:

```bash
python -m app.seed
```

**Free plan caveat:** the service sleeps after 15 minutes without traffic and takes roughly 50 seconds to wake. The first login of a demo session will be slow; the frontend's HTTP timeout is set high enough to survive it.

Start command, if you ever configure the service by hand instead:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required environment variables in production:

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | Supabase connection string |
| `JWT_SECRET` | At least 32 characters, and not the `change-me-...` placeholder. The process exits on boot otherwise. |
| `PLUGGY_CLIENT_ID` / `PLUGGY_CLIENT_SECRET` | Pluggy application credentials |
| `GEMINI_API_KEY` | Google AI Studio key |
| `CORS_ORIGINS` | Exact frontend origins, including `https://gold-queen-web.vercel.app` |
| `VERCEL_TEAM_SLUG` | `luizssantiago92`, unless the web project moves to another Vercel team |
| `CORS_ORIGIN_REGEX` | Leave unset. The app derives a preview pattern anchored to `VERCEL_TEAM_SLUG`. An empty value disables previews. |
| `ENVIRONMENT` | `production` |
| `ALLOW_REGISTRATION` | Optional. Unset (or `false`) keeps public signup closed in production. Set `true` only if new accounts should be allowed. |

## Frontend — Vercel

`gold-queen-web` deploys to Vercel under the `luizssantiago92` team. Set `VITE_API_BASE_URL` to the Render URL, then add the Vercel production domain to `CORS_ORIGINS` on the API side and redeploy the API so the new origin takes effect.

Order matters: deploy the API first, because the frontend bakes `VITE_API_BASE_URL` into the bundle at build time and needs the URL to already exist.

### Debugging CORS

A browser blocks the call whenever the response lacks `Access-Control-Allow-Origin`, and the frontend surfaces that as a generic "the API did not answer" — indistinguishable from the API being down. Check the header directly instead of guessing:

```bash
curl -sI https://gold-queen-api.onrender.com/health -H 'Origin: https://gold-queen-web.vercel.app' | grep -i access-control
```

Test the actual request as shown above, not only the `OPTIONS` preflight: Starlette answers them in separate code paths, so the preflight can succeed while the real response still omits the header.

Two failure modes look identical from the outside and are worth ruling out first: a free Render instance spun down by inactivity returns `x-render-routing: no-server` with no CORS headers, and a failed deploy leaves the previous instance serving the previous environment variables.

## Post-deploy checklist

- [ ] `GET /health` returns `pluggy_live: true` and `ai_live: true` and does not call Gemini. Leave the Render health check path on `/health` (do not point it at `?db=1` or `?deep=1`).
- [ ] `GET /health?deep=1` returns `ai_provider` when you want to probe Gemini. `GET /health?db=1` is only for the keep-alive workflow.
- [ ] `POST /v1/auth/login` works with a seeded demo user
- [ ] `POST /v1/connections/connect` as the demo user returns `403` / `demo_read_only`
- [ ] `ALLOW_REGISTRATION` is unset or `false` on the live service, unless public signup should be open
- [ ] The frontend origin is present in `CORS_ORIGINS`
- [ ] The schema step matches the database: `alembic upgrade head` on a fresh Postgres. On the existing Supabase database, `alembic stamp c7a1b5e0d942` once if `alembic_version` is missing, then `alembic upgrade head` so head is `d4e7a2b81c05` (`uq_transactions_account_pluggy_id`). Render does not run Alembic.
- [ ] `JWT_SECRET` is not the default placeholder and is at least 32 characters (`ENVIRONMENT=production` will not boot otherwise)
- [ ] `CORS_ORIGIN_REGEX` is unset or anchored to `VERCEL_TEAM_SLUG` (not `gold-queen-web-*`)

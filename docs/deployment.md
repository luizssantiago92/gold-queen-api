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

The initial schema (`users`, `bank_connections`, `accounts`, `transactions`, `chat_cache`, `chat_usage`) is already applied.

To point the API at it:

1. Get the database password in **Project Settings → Database**. Use **Reset database password** if it was never stored.
2. Build the connection string using the `psycopg2` driver:

```
postgresql+psycopg2://postgres:<password>@db.ogzmhbjadcoffaneolav.supabase.co:5432/postgres
```

Supabase shows the URI as `postgresql://`; the `+psycopg2` suffix is required by SQLAlchemy.

3. Set it as `DATABASE_URL`, then create the demo users:

```bash
python -m app.seed
```

Future schema changes go through Alembic:

```bash
alembic upgrade head
```

### Row Level Security

The frontend never talks to Supabase directly: it only calls this API, which connects over the direct Postgres connection string. The Supabase anon key is therefore never published, and authorization is enforced by the API through JWT.

Even so, RLS should be enabled so the auto-generated PostgREST endpoints reject the anon and authenticated roles. No policies are needed, because the API connects as the table owner, which bypasses RLS.

```sql
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bank_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_usage ENABLE ROW LEVEL SECURITY;
```

## API host

The API is a long-lived ASGI service, so a container host (Railway, Render, Fly.io) fits it better than serverless functions. Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required environment variables in production:

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | Supabase connection string |
| `JWT_SECRET` | Long random value, distinct from local |
| `PLUGGY_CLIENT_ID` / `PLUGGY_CLIENT_SECRET` | Pluggy application credentials |
| `GEMINI_API_KEY` | Google AI Studio key |
| `CORS_ORIGINS` | The deployed frontend origin |
| `ENVIRONMENT` | `production` |

## Frontend — Vercel

`gold-queen-web` deploys to Vercel under the `luizssantiago92` team. Set `VITE_API_BASE_URL` to the deployed API URL, then add that Vercel domain to `CORS_ORIGINS` on the API side.

## Post-deploy checklist

- [ ] `GET /health` returns `pluggy_live: true` and `ai_live: true`
- [ ] `POST /v1/auth/login` works with a seeded demo user
- [ ] `POST /v1/connections/connect` returns a real Pluggy token
- [ ] The frontend origin is present in `CORS_ORIGINS`
- [ ] `JWT_SECRET` is not the default placeholder

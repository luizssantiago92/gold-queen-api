# Deployment Guide

## Database — Supabase

1. Create a project in the `luizssantiago92` organization, region `sa-east-1` (Sao Paulo).
2. Copy the connection string from **Project Settings → Database → Connection string → URI**.
3. Convert it to the SQLAlchemy driver form:

```
postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

4. Set it as `DATABASE_URL` in the API host environment.
5. Apply the schema:

```bash
alembic upgrade head
python -m app.seed
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

# Demo operations

How to keep the Gold Queen portfolio demo useful for recruiters and visitors.

## What visitors see

The production web app (https://gold-queen-web.vercel.app) ships with:

- Pre-filled login (`queen@goldqueen.dev` / `QueenDemo123!`)
- One Pluggy Sandbox bank already synced (when seed script has been run)
- Open Finance Connect **disabled in the UI** — a modal explains demo limits
- Auto-refreshing transaction dates for demo emails so the dashboard never looks "frozen" in a new month

## 1. Create demo users

On any environment (local or Render):

```bash
python -m app.seed
```

Creates:

| Email | Password |
| --- | --- |
| `queen@goldqueen.dev` | `QueenDemo123!` |
| `squire@goldqueen.dev` | `SquireDemo123!` |

This does **not** link banks or import transactions.

## 2. Seed bank data (production)

After deploy, run once against the live API:

```bash
python -m scripts.seed_demo_connection --api https://gold-queen-api.onrender.com
```

Requires valid `PLUGGY_CLIENT_ID` and `PLUGGY_CLIENT_SECRET` in the environment where the script runs. It logs in as `queen@goldqueen.dev`, completes a sandbox sync, and populates accounts + transactions.

## 3. Demo date refresh

`app/services/demo_refresh.py` runs automatically on dashboard reads for demo emails. If Pluggy data was synced in August and the calendar is now September, transactions are shifted so the newest lands on yesterday within the current month.

No cron job is required.

## 4. Verify the demo

```bash
# Health
curl https://gold-queen-api.onrender.com/health

# Login
curl -X POST https://gold-queen-api.onrender.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"queen@goldqueen.dev","password":"QueenDemo123!"}'

# Overview (use token from login)
curl https://gold-queen-api.onrender.com/v1/dashboard/overview \
  -H "Authorization: Bearer <token>"
```

Expect non-zero `total_balance` and `month_expenses` after step 2.

## 5. Cold starts

Render's free tier hibernates after inactivity. The first request may take up to ~60 seconds. The web client retries GETs and shows a "guards are waking" message on login.

## Limitations by design

| Feature | Demo behaviour |
| --- | --- |
| Bank linking UI | Informational modal only |
| Banks connected | 1 (sandbox) |
| AI quota | 5 requests/day shared by chat + Queen's Tips |
| Gemini / Pluggy | Real keys on Render; sandbox data only |

To enable full Pluggy Connect in the UI, restore the widget flow in `gold-queen-web` (see frontend integration guide).

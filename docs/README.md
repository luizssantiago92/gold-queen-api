# Gold Queen API — Documentation

Technical documentation for the Gold Queen backend. Start with the [repository README](../README.md) for setup and endpoints.

## Guides

| Document | Audience | Description |
| --- | --- | --- |
| [architecture.md](architecture.md) | Engineers | Layers, services, data model, AI and sync flows |
| [frontend-integration.md](frontend-integration.md) | Frontend devs | Auth, JSON contracts, errors, TanStack Query keys |
| [deployment.md](deployment.md) | DevOps | Supabase, Render, environment variables, CORS |
| [demo-operations.md](demo-operations.md) | Demo / portfolio | Seeding users, linking sandbox banks, date refresh |
| [history/PRD.md](history/PRD.md) | Archive | Original product brief. Current behavior is the README and the guides above |

## Quick links

- **OpenAPI:** `/openapi.json` and `/docs` on any running instance
- **Health:** `GET /health` → `{ "status": "ok", "pluggy_live": bool, "ai_live": bool }` with no outbound calls and no `environment`. `GET /health?db=1` also runs `SELECT 1` and adds `"database":"ok"` (503 when unreachable). `GET /health?deep=1` is the only Gemini probe and adds `ai_provider`. The `Keep alive` workflow calls `?db=1` twice a week so the free Supabase project never pauses. Render's health check stays on `/health`.
- **Root:** `GET /` redirects to `/docs` (307).
- **Production docs:** https://gold-queen-api.onrender.com/docs
- **Frontend repo:** https://github.com/luizssantiago92/gold-queen-web

## Conventions

- Monetary values are `Decimal` serialized as **strings** with two decimal places.
- Dates use ISO `YYYY-MM-DD`.
- Errors return `{ "detail": string, "code": string }`.
- AI-audited records expose `is_guarded: true`; fallbacks use `false`.

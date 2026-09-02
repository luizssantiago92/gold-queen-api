# Gold Queen API — Documentation

Technical documentation for the Gold Queen backend. Start with the [repository README](../README.md) for setup and endpoints.

## Guides

| Document | Audience | Description |
| --- | --- | --- |
| [architecture.md](architecture.md) | Engineers | Layers, services, data model, AI and sync flows |
| [frontend-integration.md](frontend-integration.md) | Frontend devs | Auth, JSON contracts, errors, TanStack Query keys |
| [deployment.md](deployment.md) | DevOps | Supabase, Render, environment variables, CORS |
| [demo-operations.md](demo-operations.md) | Demo / portfolio | Seeding users, linking sandbox banks, date refresh |

## Quick links

- **OpenAPI:** `/openapi.json` and `/docs` on any running instance
- **Health:** `GET /health` → `{ "status": "ok", "pluggy_live": bool, "ai_live": bool }`
- **Production:** https://gold-queen-api.onrender.com
- **Frontend repo:** https://github.com/luizssantiago92/gold-queen-web

## Conventions

- Monetary values are `Decimal` serialized as **strings** with two decimal places.
- Dates use ISO `YYYY-MM-DD`.
- Errors return `{ "detail": string, "code": string }`.
- AI-audited records expose `is_guarded: true`; fallbacks use `false`.

# ADR 0004: Vercel hosts the frontend, not this API

- Status: Accepted
- Recorded: 2026-10-07 (the service already runs this way)

## Context

The interface is [gold-queen-web](https://github.com/luizssantiago92/gold-queen-web), a separate Vite app deployed on Vercel under the `luizssantiago92` team. This repository serves JSON. The browser calls it cross-origin, so the allowed origins have to be explicit.

## Decision

The web app stays on Vercel. This API allows exact origins from `CORS_ORIGINS`. The default list is `http://localhost:5173`, `http://localhost:3000`, `https://gold-queen-web.vercel.app`, and `https://gold-queen-web-<team>.vercel.app`. When `CORS_ORIGIN_REGEX` is unset, preview hosts must match `^https://gold-queen-web-[a-z0-9-]+-<team>\.vercel\.app$`, where `<team>` is `VERCEL_TEAM_SLUG` (default `luizssantiago92`). An empty regex disables previews. `render.yaml` sets the team slug and leaves the regex unset.

`VITE_API_BASE_URL` is baked into the web bundle at build time, so the API URL has to exist before that build.

## Consequences

This repository does not build or deploy the UI. A new production origin is added to `CORS_ORIGINS` and the API is redeployed before the browser can call it. Credentials are allowed on CORS responses (`allow_credentials=True`) together with the explicit origin list, not a wildcard origin.

## Alternatives

Serving the SPA from FastAPI would tie the UI release to this process. A pattern of `gold-queen-web-*` without the team slug would accept a lookalike project on another Vercel account; `app/core/config.py` refuses that shape for the derived regex.

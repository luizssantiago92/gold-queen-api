<!-- retornatus-meta
{
  "change_id": "C-0003",
  "schema_version": 1
}
-->

# Situation

## Demand

API-M1, API-M2, API-M6, and API-B8 on the Render single-process uvicorn API: connection connect and sync are async handlers that use the synchronous SQLAlchemy session and call blocking Gemini code (httpx.Client with a 30s timeout and time.sleep on retries), so one sync stalls every other request. GET /health calls Gemini on every request, exposes environment, and is the Render health check. GET / returns 404. Responses lack nosniff, HSTS, referrer policy, and frame denial. gold-queen-web does not read /health fields. Keep-alive greps database ok. CORS stays limited to the web app origin.

## Project context

# Project

Retornatus project continuity notes live here.

Agents and humans express intent. Retornatus owns structure.

## Repo signals (inferred)

- stack manifests: `pyproject.toml`, `requirements.txt`
- tests: tests/, pytest (pyproject)
- ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- architecture: docs/architecture.md; AGENTS.md
- code path present: `app/main.py`
- health endpoint symbols already present in app/main.py
- Retornatus already initialized

## Known facts

- Demand stated: API-M1, API-M2, API-M6, and API-B8 on the Render single-process uvicorn API: connection connect and sync are async handlers that use the synchronous SQLAlchemy session and call blocking Gemini code (httpx.Client with a 30s timeout and time.sleep on retries), so one sync stalls every other request. GET /health calls Gemini on every request, exposes environment, and is the Render health check. GET / returns 404. Responses lack nosniff, HSTS, referrer policy, and frame denial. gold-queen-web does not read /health fields. Keep-alive greps database ok. CORS stays limited to the web app origin.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Move synchronous database and Gemini work off the event loop for the connection handlers, keeping async Pluggy HTTP on the loop. Make GET /health local: no outbound calls and no environment field; db=1 still runs SELECT 1 and returns database ok; deep=1 is the only Gemini probe. Redirect GET / to /docs. Add nosniff, HSTS, no-referrer, and X-Frame-Options DENY without CSP. Do not add dependencies or change unrelated behavior.
- DONE criterion: pytest shows connect and sync run synchronous work off the event loop
- DONE criterion: pytest shows GET /health omits environment and skips the provider probe unless deep=1, and db=1 still returns database ok
- DONE criterion: pytest shows GET / redirects to /docs
- DONE criterion: pytest shows nosniff, HSTS, no-referrer, and DENY frame headers while CORS for the web origin still works

## Constraints

- Prefer pytest for automated verification (inferred from repo)
- Prefer pytest for automated verification (inferred from repo)

## Assumptions

- (none)

## Ambiguities

- (none)

## Missing decisions

- (none)

## Contract readiness

- Sufficient: **yes**
- Rationale: Demand, WHAT, and DONE are sufficiently clear; repo/kickoff signals incorporated; no material requirements ambiguity detected

## Agent narrative

Single uvicorn worker on Render free. The Pluggy client is async httpx. Other routers are already plain def functions, so FastAPI runs them in the threadpool. The public gold-queen-web repo does not read /health. HSTS is sent on every response because user agents ignore it over plain HTTP, which keeps local HTTP usable and production HTTPS covered without an environment branch.

## Reopened Situation

Replaced the vague word works in the header criterion with an observable CORS header.

<!-- retornatus-meta
{
  "change_id": "C-0007",
  "schema_version": 1
}
-->

# Situation

## Demand

Audit items API-B1, API-B2, API-B3, API-B4, API-B5, API-B6, API-B9, API-B10, and API-B11 are still present on main. The bcrypt replacement from C-0004 and the security headers from C-0003 stay as they are. Fix the open items, cover them with tests, add one Alembic migration that is safe for the production Supabase database, polish the README, and record the work as a new Change. Do not bump the package version and do not merge.

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

- Demand stated: Audit items API-B1, API-B2, API-B3, API-B4, API-B5, API-B6, API-B9, API-B10, and API-B11 are still present on main. The bcrypt replacement from C-0004 and the security headers from C-0003 stay as they are. Fix the open items, cover them with tests, add one Alembic migration that is safe for the production Supabase database, polish the README, and record the work as a new Change. Do not bump the package version and do not merge.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Proposed WHAT: Honor Accept-Language for queen tips when the locale query is omitted. Store the tips cache as JSON and treat a legacy row as a miss. Paginate dashboard transactions with SQL offset, limit, and count. Refresh demo dates on login instead of on dashboard reads. Add a unique user-and-date constraint on chat usage after deduping rows, and consume quota with an atomic upsert on Postgres and SQLite. Check a dummy bcrypt hash when a login email is unknown. Send the Gemini key in the x-goog-api-key header. Retry HTTP 429 with bounded backoff that honors Retry-After. Store timestamps as timezone-aware UTC so JSON includes an offset. Add a monochrome queen icon, a Swagger screenshot, and a one-minute trial to the README, and list the fixes under Unreleased.
- DONE criterion: Queen tips follow Accept-Language when the locale query is omitted and follow the query when it is set.
- DONE criterion: A tips cache row stored as JSON round-trips, and an unparsable legacy row is a cache miss.
- DONE criterion: Transaction pages apply SQL offset and limit and report the full count.
- DONE criterion: Demo dates move on login and a dashboard read does not move them.
- DONE criterion: Concurrent quota consumption stops at the daily limit and leaves one usage row.
- DONE criterion: An unknown login email still runs a password hash check.
- DONE criterion: Gemini requests send the key in a header and omit it from the query string.
- DONE criterion: A 429 response is retried and the wait follows Retry-After up to a cap.
- DONE criterion: Serialized timestamps include a timezone offset.
- DONE criterion: The changelog Unreleased section lists these fixes and the version field stays 1.0.0.
- DONE criterion: The file "README.md" shows the monochrome queen mark, a Swagger screenshot, and a one-minute trial.
- DONE criterion: A review note covers the migration that dedupes quota rows and stores timestamps in UTC.

## Constraints

- Prefer pytest for automated verification (inferred from repo)
- Prefer pytest for automated verification (inferred from repo)

## Assumptions

- Situation placeholder used — treat as unanalyzed unless Demand is trivial

## Ambiguities

- (none)

## Missing decisions

- (none)

## Contract readiness

- Sufficient: **yes**
- Rationale: Demand, WHAT, and DONE are sufficiently clear; repo/kickoff signals incorporated; no material requirements ambiguity detected

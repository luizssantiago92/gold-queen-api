# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Current requirements, a PostgreSQL entity diagram, architecture decision records, and a security policy. The original brief stays in `docs/history/`.

### Changed

- Postgres schema comes only from Alembic. Startup `create_all` runs for SQLite (local quick-start and tests) and does not run against Postgres. An existing Supabase database is aligned once with `alembic stamp head`; a fresh database uses `alembic upgrade head`.
- Queen's Tips honor `Accept-Language` when the `locale` query is omitted. An explicit `locale` still wins.
- The tips cache is stored as JSON. A legacy row that cannot be parsed is a cache miss.
- `GET /v1/dashboard/transactions` pages with SQL `OFFSET`/`LIMIT` and `COUNT`.
- Demo transaction dates refresh on login. Dashboard reads no longer write.
- Daily quota consumption is one atomic upsert. `chat_usage` has a unique `(user_id, usage_date)` constraint, and the same idea covers per-visitor demo rows.
- Login checks a dummy bcrypt hash when the email is unknown.
- The Gemini API key is sent in the `x-goog-api-key` header.
- HTTP 429 from the model provider is retried, honoring `Retry-After` up to 8 seconds.
- Timestamps are stored as timezone-aware UTC, so JSON includes an offset.

### Fixed

- Bank sync skips a repeated Pluggy transaction id in one fetch and upserts on `(account_id, pluggy_transaction_id)`, so the same movement is not inserted twice. Alembic revision `d4e7a2b81c05` deletes stored copies that share a Pluggy id in one account, and copies that share account, description, amount, and date, keeping the oldest id, then adds `uq_transactions_account_pluggy_id`. Render does not run Alembic; apply the revision once with `alembic upgrade head`.

### Security

- Unknown emails no longer skip the password check.

## [1.0.0] - 2026-10-03

### Added

- FastAPI service that syncs Open Finance accounts and transactions through Pluggy, categorizes them with Gemini behind a closed vocabulary, and serves a dashboard, Queen's Tips, and chat.
- JWT login and bcrypt password hashes. Public demo accounts `queen@goldqueen.dev` and `squire@goldqueen.dev` are read-only.
- Shared daily AI quota for chat and Queen's Tips, with a same-day chat cache. Demo quota is counted per visitor IP.
- Sync that inserts a transaction only when `pluggy_transaction_id` is new, and that checks Pluggy `clientUserId` before claiming a live item.
- Offline Pluggy simulator and rule-based AI fallbacks when credentials are absent. Fallback rows set `is_guarded` to false.
- English and Portuguese responses for the advisor and chat.
- GitHub Actions CI (ruff, ruff format, mypy, pip-audit, pytest with a branch-coverage floor of 85), CodeQL for Python and Actions, and Dependabot.
- Retornatus change records C-0001 through C-0005.

### Changed

- C-0001: tool config in `pyproject.toml`, ruff format, and a clean mypy run.
- C-0002: third-party actions pinned by commit SHA, coverage floor, CodeQL, and Dependabot.
- C-0003: sync and startup SQL moved off the event loop, a light `/health` probe, and security headers on every response.
- C-0004: `passlib` replaced by the `bcrypt` package. Existing `$2b$` hashes still verify. Registration rejects a password longer than 72 UTF-8 bytes.
- C-0005: one error body, `detail` and `code`, plus optional `errors` on validation. OpenAPI tags, summaries, examples, and error responses. The API version is read from `pyproject.toml`.

### Security

- Production startup refuses a default or short `JWT_SECRET`.
- Login attempts are limited in process memory.
- CORS preview origins are scoped to the Vercel team slug.
- Validation errors do not echo submitted field values. Unexpected failures do not return a traceback.

[Unreleased]: https://github.com/luizssantiago92/gold-queen-api/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/luizssantiago92/gold-queen-api/releases/tag/v1.0.0

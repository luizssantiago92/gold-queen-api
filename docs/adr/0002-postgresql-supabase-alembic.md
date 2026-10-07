# ADR 0002: PostgreSQL on Supabase, schema owned by Alembic

- Status: Accepted
- Recorded: 2026-10-07 (the service already runs this way)

## Context

Treasury rows, the chat cache, and the daily quota have to survive a process restart. Production is a Supabase Postgres project in `sa-east-1` on the free plan. Local quick-start and the test suite need a database with no network. An earlier startup path called `SQLModel.metadata.create_all` for every engine, so production could drift from the migrations.

## Decision

Tables are SQLModel classes in `app/models/entities.py`. Alembic is the only PostgreSQL schema source. Head is `d4e7a2b81c05`. `init_db` calls `create_all` only when the URL backend is SQLite. A fresh Postgres, including `docker-compose.yml`, is built with `alembic upgrade head`. Render starts uvicorn and does not run migrations.

The production database was created by the Supabase migrations `initial_schema` and `enable_row_level_security`, not by Alembic. `alembic upgrade head` must not be the first command on a database that has no `alembic_version` row: that tries to create tables that already exist. After the live schema is confirmed to match `c7a1b5e0d942`, `alembic stamp c7a1b5e0d942` records that revision without changing tables. Later revisions, including `d4e7a2b81c05` (transaction dedupe and `uq_transactions_account_pluggy_id`), are applied with `alembic upgrade head`. Render does not run that command.

`DATABASE_URL` uses the SQLAlchemy driver suffix `postgresql+psycopg2` and the session pooler host. The direct host publishes only an IPv6 address.

## Consequences

Schema changes are reviewable migration files. SQLite tests do not prove PostgreSQL-only behavior; `tests/test_database.py` and `tests/test_migration.py` cover the Postgres path when a server is available. Row-level security is a Supabase setting, not an Alembic revision. See [data-model.md](../data-model.md).

## Alternatives

`create_all` on Postgres was removed so startup cannot invent columns the migrations do not have. SQLite in production would not match the pooler deployment or `timestamptz`. The historical in-memory cache does not survive a Render restart; the cache and the quota counter are tables.

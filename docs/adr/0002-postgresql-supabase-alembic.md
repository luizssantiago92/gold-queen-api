# ADR 0002: PostgreSQL on Supabase, schema owned by Alembic

- Status: Accepted
- Recorded: 2026-10-07 (the service already runs this way)

## Context

Treasury rows, the chat cache, and the daily quota have to survive a process restart. Production is a Supabase Postgres project in `sa-east-1` on the free plan. Local quick-start and the test suite need a database with no network. An earlier startup path called `SQLModel.metadata.create_all` for every engine, so production could drift from the migrations.

## Decision

Tables are SQLModel classes in `app/models/entities.py`. Alembic is the only PostgreSQL schema source. Head is `c7a1b5e0d942`. `init_db` calls `create_all` only when the URL backend is SQLite. A fresh Postgres, including `docker-compose.yml`, is built with `alembic upgrade head`. Render starts uvicorn and does not run migrations.

The production database was created by the Supabase migrations `initial_schema` and `enable_row_level_security`, not by Alembic. `alembic upgrade head` must not be run there. After the live schema is confirmed to match head, `alembic stamp head` records `alembic_version` without changing tables. Later changes are new revisions applied with `alembic upgrade head` before or with the deploy.

`DATABASE_URL` uses the SQLAlchemy driver suffix `postgresql+psycopg2` and the session pooler host. The direct host publishes only an IPv6 address.

## Consequences

Schema changes are reviewable migration files. SQLite tests do not prove PostgreSQL-only behavior; `tests/test_database.py` and `tests/test_migration.py` cover the Postgres path when a server is available. Row-level security is a Supabase setting, not an Alembic revision. See [data-model.md](../data-model.md).

## Alternatives

`create_all` on Postgres was removed so startup cannot invent columns the migrations do not have. SQLite in production would not match the pooler deployment or `timestamptz`. The historical in-memory cache does not survive a Render restart; the cache and the quota counter are tables.

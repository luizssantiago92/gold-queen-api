<!-- retornatus-meta
{
  "change_id": "C-0008",
  "schema_version": 1
}
-->

# Situation

## Demand

Finding API-M4: the FastAPI lifespan calls SQLModel.metadata.create_all, so production Postgres can diverge from Alembic. The production Supabase database was created by Supabase migrations, has no alembic_version table, and revision c7a1b5e0d942 was already applied by hand. Register this as the next Retornatus Change after C-0007, open one pull request titled chore(db): single source of truth for schema, and do not merge it.

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

- Demand stated: Finding API-M4: the FastAPI lifespan calls SQLModel.metadata.create_all, so production Postgres can diverge from Alembic. The production Supabase database was created by Supabase migrations, has no alembic_version table, and revision c7a1b5e0d942 was already applied by hand. Register this as the next Retornatus Change after C-0007, open one pull request titled chore(db): single source of truth for schema, and do not merge it.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Proposed WHAT: Call SQLModel.metadata.create_all only when the database URL backend is SQLite, which covers local quick-start and tests. On Postgres, including production, startup must not create or alter tables; the schema comes only from Alembic. Confirm that the current Alembic head matches the SQLModel models on a fresh Postgres. Document one schema source of truth: fresh databases run alembic upgrade head; an existing database created outside Alembic is aligned once with alembic stamp head after the schema is confirmed to match; every later schema change is a new Alembic migration applied with alembic upgrade head before or with the deploy. State that row-level security is already enabled on the six Supabase tables. Record the change in CHANGELOG Unreleased. Do not add a migration unless the models and head differ, do not bump the package version, and do not touch production.
- DONE criterion: Process startup calls SQLModel.metadata.create_all only when the database URL backend is SQLite.
- DONE criterion: A Postgres database URL does not call create_all and does not issue schema DDL at startup.
- DONE criterion: Tests cover the SQLite create_all branch and the Postgres skip branch.
- DONE criterion: On a fresh Postgres, alembic upgrade head followed by alembic check reports no model drift. The head revision stays c7a1b5e0d942 unless a migration was required to remove drift.
- DONE criterion: docs/deployment.md states that Alembic is the only schema source, that a fresh database runs alembic upgrade head, that an existing database created outside Alembic is aligned once with alembic stamp head after the schema matches, and that later schema changes are new migrations applied with alembic upgrade head. It states that RLS is already enabled on the six Supabase tables.
- DONE criterion: The README describes the same Alembic source of truth for Postgres and that SQLite local and test startup still creates tables.
- DONE criterion: CHANGELOG Unreleased lists this change and the package version stays 1.0.0.

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

## Reopened Situation

Reword the changelog criterion so Assurance does not treat the word package as a build claim.

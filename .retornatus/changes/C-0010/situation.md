<!-- retornatus-meta
{
  "change_id": "C-0010",
  "schema_version": 1
}
-->

# Situation

## Demand

Live Pluggy sandbox demo (Pluggy Bank, synced 2026-08-28) stores repeated transactions in one account: NETFLIX.COM, SPOTIFY AB, SMART FIT ACADEMIA, and SALARIO EMPRESA XYZ LTDA at R$ 8500 on the same date. Monthly income shows R$ 34000. Sync must be idempotent and existing copies must be removed.

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

- Demand stated: Live Pluggy sandbox demo (Pluggy Bank, synced 2026-08-28) stores repeated transactions in one account: NETFLIX.COM, SPOTIFY AB, SMART FIT ACADEMIA, and SALARIO EMPRESA XYZ LTDA at R$ 8500 on the same date. Monthly income shows R$ 34000. Sync must be idempotent and existing copies must be removed.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Make sync idempotent: skip a repeated Pluggy transaction id inside one fetch, and upsert on (account_id, pluggy_transaction_id). Add an Alembic revision that deletes existing copies that share (account_id, pluggy_transaction_id) and copies that share (account_id, description, amount, transaction_date), keeping the oldest id in each group, then adds unique constraint uq_transactions_account_pluggy_id. Downgrade drops that constraint and does not restore deleted rows.
- DONE criterion: A fetch that repeats one Pluggy transaction id stores a single row for that account.
- DONE criterion: A later sync of the same (account_id, pluggy_transaction_id) updates description, amount, and date in place and does not insert another row.
- DONE criterion: The migration deletes extra rows that share (account_id, pluggy_transaction_id), keeping the oldest id, and deletes extra rows that share (account_id, description, amount, transaction_date), keeping the oldest id.
- DONE criterion: The migration adds unique constraint uq_transactions_account_pluggy_id. Inserting the same (account_id, pluggy_transaction_id) again fails. Downgrade drops the constraint and does not restore deleted rows.
- DONE criterion: Tests cover the in-fetch skip, the upsert, and the migration upgrade and downgrade.
- DONE criterion: CHANGELOG Unreleased records the dedupe. docs/data-model.md, docs/deployment.md, and ADR 0002 name the new head and the constraint. The version in pyproject.toml stays 1.0.0.
- DONE criterion: A review note covers the migration. A ship rollback note says rollback is alembic downgrade c7a1b5e0d942, which drops the constraint and does not restore deleted rows, and that Render does not run Alembic so the owner runs alembic upgrade head once after merge.

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

Constraints: do not change gold-queen-web; do not merge; code, tests, and docs stay in English. Render does not run Alembic.

<!-- retornatus-meta
{
  "change_id": "C-0012",
  "schema_version": 1
}
-->

# Situation

## Demand

Production sync of Pluggy Bank on 2026-08-28 stored SALARIO EMPRESA XYZ LTDA four times because each copy had a different pluggy_transaction_id. The unique constraint on (account_id, pluggy_transaction_id) does not stop a later fetch that mints a new id for the same description, amount, and date. app.seed does not insert transactions and must stay unchanged. Credit-card bill payments are out of scope.

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

- Demand stated: Production sync of Pluggy Bank on 2026-08-28 stored SALARIO EMPRESA XYZ LTDA four times because each copy had a different pluggy_transaction_id. The unique constraint on (account_id, pluggy_transaction_id) does not stop a later fetch that mints a new id for the same description, amount, and date. app.seed does not insert transactions and must stay unchanged. Credit-card bill payments are out of scope.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: In sync_item, skip a remote transaction whose (account_id, description, amount in cents, transaction_date) already exists, and apply that same key inside one fetch so four sandbox salary rows become one. A code comment records that two legitimate purchases with the same description, cent amount, and day collapse into one row.
- DONE criterion: One fetch that repeats SALARIO EMPRESA XYZ LTDA four times under different Pluggy ids stores a single row.
- DONE criterion: A later sync that returns the same account, description, amount in cents, and date under a new Pluggy id does not insert another row.
- DONE criterion: Tests cover the in-fetch case and the cross-sync case.
- DONE criterion: A code comment states that two legitimate purchases with the same description, cent amount, and day collapse into one row.
- DONE criterion: app.seed is unchanged, and credit-card bill payments stay in expense totals.

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

Production copies shared a description, cent amount, and date and differed only by pluggy_transaction_id. They landed in one sync commit. sync_item upserts only on (account_id, pluggy_transaction_id). The fingerprint delete in d4e7a2b81c05 does not run again. app.seed only creates users. Card-bill payments remain expenses.

## Reopened Situation

The migration header still said a later sync ignores the description key. The header now matches sync.py. No new revision.

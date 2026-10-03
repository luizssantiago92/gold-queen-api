<!-- retornatus-meta
{
  "change_id": "C-0004",
  "schema_version": 1
}
-->

# Situation

## Demand

Dependabot pull requests 9 and 10 fail CI. PR 9 bumps fastapi, uvicorn, sqlmodel, psycopg2-binary, alembic, pydantic-settings, email-validator, and PyJWT, and mypy rejects optional persisted ids in app/services/sync.py. PR 10 bumps bcrypt to 5.0.0, and unmaintained passlib 1.7.4 breaks tests by probing bcrypt with a password longer than 72 bytes. Both also fail the Retornatus omission gate because the diff touches pyproject.toml and no Change. Apply those pins, replace passlib with the bcrypt package, keep existing dollar-2b hashes valid, reject registration passwords longer than 72 bytes, and let Dependabot manifest-only pull requests pass omission without weakening the gate for human or agent pull requests.

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

- Demand stated: Dependabot pull requests 9 and 10 fail CI. PR 9 bumps fastapi, uvicorn, sqlmodel, psycopg2-binary, alembic, pydantic-settings, email-validator, and PyJWT, and mypy rejects optional persisted ids in app/services/sync.py. PR 10 bumps bcrypt to 5.0.0, and unmaintained passlib 1.7.4 breaks tests by probing bcrypt with a password longer than 72 bytes. Both also fail the Retornatus omission gate because the diff touches pyproject.toml and no Change. Apply those pins, replace passlib with the bcrypt package, keep existing dollar-2b hashes valid, reject registration passwords longer than 72 bytes, and let Dependabot manifest-only pull requests pass omission without weakening the gate for human or agent pull requests.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Pin the PR 9 updates and bcrypt 5.0.0 in requirements.txt and pyproject.toml, remove passlib and types-passlib, hash and verify with bcrypt.hashpw and bcrypt.checkpw, narrow persisted sync ids with require_id, reject registration passwords over 72 bytes, and set RETORNATUS_OMISSION to warn only for Dependabot pull requests whose diff is limited to dependency manifests.
- DONE criterion: pytest shows registration rejects a password longer than 72 bytes with status 422 and accepts a password of 72 bytes
- DONE criterion: pytest shows a stored passlib bcrypt hash that starts with $2b$ still verifies and hash_password emits a $2b$ hash
- DONE criterion: A review note covers the Dependabot omission setting in the Retornatus workflow.

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

Registration already caps password length at 128 characters, which can exceed 72 UTF-8 bytes. Production hashes are passlib bcrypt strings with the $2b$ prefix. Retornatus 1.9.1 has no path or author exemption; the action treats any pyproject.toml or uv.lock change as code. The supported knob is RETORNATUS_OMISSION warn versus fail. A job-level if that skips retornatus-gates would report success for the required check and would also skip the suppressions gate.

<!-- retornatus-meta
{
  "change_id": "C-0002",
  "schema_version": 1
}
-->

# Situation

## Demand

Harden GitHub Actions: pin third-party actions to full commit SHAs, least-privilege permissions, cancel stale pull-request runs, enforce a measured coverage floor, add weekly Dependabot for pip and github-actions, and add CodeQL for Python and Actions.

## Project context

# Project

Retornatus project continuity notes live here.

Agents and humans express intent. Retornatus owns structure.

## Repo signals (inferred)

- stack manifests: `pyproject.toml`, `requirements.txt`
- tests: tests/, pytest (pyproject)
- ci: `ci.yml`, `keep-alive.yml`, `retornatus.yml`
- architecture: docs/architecture.md; AGENTS.md
- code path present: `app/main.py`
- health endpoint symbols already present in app/main.py
- Retornatus already initialized

## Known facts

- Demand stated: Harden GitHub Actions: pin third-party actions to full commit SHAs, least-privilege permissions, cancel stale pull-request runs, enforce a measured coverage floor, add weekly Dependabot for pip and github-actions, and add CodeQL for Python and Actions.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Pin actions/checkout and actions/setup-python to verified tag SHAs in CI, set contents read, persist-credentials false, a job timeout, and concurrency that cancels older runs of the same pull request. Keep ruff check, ruff format --check, mypy, pip-audit, and pytest. Measure coverage and fail under the current total floored to a multiple of 5, configured in pyproject.toml, with pytest-cov pinned in the dev requirements. Add weekly Dependabot for pip and github-actions in America/Sao_Paulo, grouping minor and patch updates, with a low open-PR limit and commit prefixes chore(deps) and ci(deps). Add a CodeQL workflow for python and actions, pinned to the latest v4 commit, on push and pull request to main plus a weekly cron, with least-privilege permissions and build-mode none. Do not change application behavior or requirements.txt. Leave keep-alive and the Retornatus workflow logic unchanged.
- DONE criterion: pytest, ruff check, ruff format, and mypy pass
- DONE criterion: A review note covers pinned workflows and Dependabot.
- DONE criterion: The coverage floor is documented in pyproject.toml.

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

Python 3.11 FastAPI app. Render installs requirements.txt and must not be retargeted. CI installs requirements-dev.txt and already runs ruff check, ruff format --check, mypy, pip-audit, and pytest. Workflow files are ship-sensitive, so this change needs an actionlint run, a ship rollback note, and a review note. keep-alive.yml and retornatus.yml already use least-privilege permissions; retornatus.yml already pins checkout by SHA and keeps luizssantiago92/retornatus on the owner tag v1.

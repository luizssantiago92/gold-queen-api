<!-- retornatus-meta
{
  "change_id": "C-0001",
  "schema_version": 1
}
-->

# Situation

## Demand

Audit items API-M10 and API-M3: no pyproject.toml, ruff pinned at 0.8.4, unformatted Python, four mypy errors, many type-ignore comments, and an unused google-genai dependency while the README names the Google GenAI SDK.

## Project context

# Project

Retornatus project continuity notes live here.

Agents and humans express intent. Retornatus owns structure.

## Repo signals (inferred)

- stack manifests: `requirements.txt`
- tests: tests/
- ci: `ci.yml`, `keep-alive.yml`, `retornatus.yml`
- architecture: docs/architecture.md; AGENTS.md
- code path present: `app/main.py`
- health endpoint symbols already present in app/main.py
- Retornatus already initialized

## Known facts

- Demand stated: Audit items API-M10 and API-M3: no pyproject.toml, ruff pinned at 0.8.4, unformatted Python, four mypy errors, many type-ignore comments, and an unused google-genai dependency while the README names the Google GenAI SDK.
- Repo: stack manifests: `requirements.txt`
- Repo: tests: tests/
- Repo: ci: `ci.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Add pyproject.toml for ruff, pytest, mypy, and coverage; keep requirements files for Render and CI; bump ruff to the current release; format Python in its own commit and record that SHA in .git-blame-ignore-revs; fix the four mypy errors and narrow persisted ids without changing behavior; add mypy and format check to CI; remove google-genai and correct the README. Constraints: do not change runtime behavior; do not squash the format commit; keep requirements files because Render and CI install from them.
- DONE criterion: pytest, ruff check, and mypy pass for app and tests
- DONE criterion: README documents Gemini REST via httpx, not the GenAI SDK.
- DONE criterion: The format-only commit is documented in .git-blame-ignore-revs.
- DONE criterion: A review note covers the CI workflow tool steps.

## Constraints

- (none)

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

Python 3.11 FastAPI app. Render runs pip install -r requirements.txt. CI installs requirements-dev.txt then ruff check and pytest. pytest.ini holds pytest options. Gemini calls the REST API through httpx. Retornatus required checks invoke uv and ruff still lists a src directory this repo does not have. Workflow and Alembic paths are ship-sensitive, so CI edits need a review note and an actionlint run plus a ship rollback note.

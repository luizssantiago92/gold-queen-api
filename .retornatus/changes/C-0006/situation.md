<!-- retornatus-meta
{
  "change_id": "C-0006",
  "schema_version": 1
}
-->

# Situation

## Demand

Publish a recruiter-facing README, an MIT license, and a changelog, archive the historical product brief, and record project metadata. The package version in pyproject.toml is 1.0.0 and stays 1.0.0 because OpenAPI reads it.

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

- Demand stated: Publish a recruiter-facing README, an MIT license, and a changelog, archive the historical product brief, and record project metadata. The package version in pyproject.toml is 1.0.0 and stays 1.0.0 because OpenAPI reads it.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Rewrite README.md in English for a backend recruiter using only behavior present in the code and the current docs. Add an MIT LICENSE for Luiz Santiago in 2026 and a Keep a Changelog with an empty Unreleased section and a 0.1.0 section dated 2026-10-03. Move the root PRD into docs/history and fix links that pointed at it. Add license, authors, readme, and project URLs to pyproject.toml without changing version 1.0.0.
- DONE criterion: The file "README.md" documents the live web app, the API docs, and both demo account emails.
- DONE criterion: The file "LICENSE" documents an MIT copyright for Luiz Santiago in 2026.
- DONE criterion: The file "CHANGELOG.md" documents version 0.1.0 dated 2026-10-03 and contains an empty Unreleased section.
- DONE criterion: The history document "PRD.md" exists under the docs history directory and the repository root no longer contains that file.
- DONE criterion: The file "pyproject.toml" documents license, authors, readme, and project urls, and its version field stays 1.0.0.

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

The repository is a FastAPI portfolio API. Root PRD.md is marked historical. pyproject.toml version is 1.0.0 and app/__init__.py reads that value for OpenAPI. Retornatus 1.9.1 treats a pyproject.toml diff as code, so this Change exists to satisfy the omission gate.

## Reopened Situation

DONE lines for the license and the changelog now say documented so Assurance asks for a repository observation.

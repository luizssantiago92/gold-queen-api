<!-- retornatus-meta
{
  "change_id": "C-0009",
  "schema_version": 1
}
-->

# Situation

## Demand

Open one docs-only pull request that adds portfolio-grade documentation grounded strictly in the current code: docs/requirements.md (RF and RNF, traceable to code, endpoints, or tests; historical PRD stays in docs/history/), docs/data-model.md (Mermaid erDiagram from SQLAlchemy models and Alembic), docs/adr/ MADR records for the real decisions plus an index, SECURITY.md at the repo root, and links from docs/README.md and the main README docs section. CI stays green. Govern the work with a Retornatus Change that reaches SATISFIED. Do not change gold-queen-web.

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

- Demand stated: Open one docs-only pull request that adds portfolio-grade documentation grounded strictly in the current code: docs/requirements.md (RF and RNF, traceable to code, endpoints, or tests; historical PRD stays in docs/history/), docs/data-model.md (Mermaid erDiagram from SQLAlchemy models and Alembic), docs/adr/ MADR records for the real decisions plus an index, SECURITY.md at the repo root, and links from docs/README.md and the main README docs section. CI stays green. Govern the work with a Retornatus Change that reaches SATISFIED. Do not change gold-queen-web.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Add English documentation that describes only behavior present in this repository: current functional and non-functional requirements, a Mermaid entity diagram of the real PostgreSQL schema with table notes, short MADR architecture decision records for the decisions already implemented, a root security policy, and links from the documentation index and the main README. Leave application code, migrations, and the package version unchanged.
- DONE criterion: docs/requirements.md lists current functional requirements as RF-xx and non-functional requirements as RNF-xx covering security, performance and cold start, availability, privacy and LGPD-minded data handling, observability, and cost, each traceable to code, an endpoint, or a test where possible, and it states that docs/history/PRD.md is historical.
- DONE criterion: docs/data-model.md contains a Mermaid erDiagram derived from the SQLAlchemy models and Alembic migrations, plus a short description of each table covering keys, relationships, notable constraints, and the row-level security note.
- DONE criterion: docs/adr/ contains short MADR-style records with context, decision, consequences, and alternatives for FastAPI, PostgreSQL on Supabase plus Alembic, Render hosting and its cold start, Vercel for the frontend, JWT plus bcrypt plus the login rate limit, Gemini categorization with guardrails, rule fallback, and daily quota, the read-only demo account, and Retornatus governance, plus docs/adr/README.md as an index.
- DONE criterion: SECURITY.md at the repository root states supported versions, how to report a vulnerability privately, and a summary of security controls that the code actually implements.
- DONE criterion: docs/README.md and the documentation section of README.md link to the requirements, data model, ADR index, and SECURITY.md.
- DONE criterion: The diff does not change application behavior: app/, tests/, alembic/, and the version in pyproject.toml stay as they are.

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

Demand, WHAT, and DONE are sufficiently clear from the request and the current repository. Documentation must describe implemented behavior only. The historical PRD stays in docs/history/. The gold-queen-web repository is out of scope. English prose. No Skill: the human declined specialization because the source of truth is this codebase.

## Reopened Situation

Reworded the security-policy criterion so Assurance can bind a repository observation. The policy content is unchanged.

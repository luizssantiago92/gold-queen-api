<!-- retornatus-meta
{
  "change_id": "C-0011",
  "schema_version": 1
}
-->

# Situation

## Demand

The chat scope guard refused 'Quais foram minhas 3 maiores transações este mês?' as off-topic because ç and ê were not recognized. Matching must fold case and strip accents before comparing the question with the keyword list. Genuinely off-topic questions stay refused. Do not run the production migration.

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

- Demand stated: The chat scope guard refused 'Quais foram minhas 3 maiores transações este mês?' as off-topic because ç and ê were not recognized. Matching must fold case and strip accents before comparing the question with the keyword list. Genuinely off-topic questions stay refused. Do not run the production migration.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Normalize the chat scope guard with unicodedata NFKD accent stripping and casefold on the user question and on the in-scope and out-of-scope keyword lists, then match. Accented, unaccented, and uppercase treasury questions in Portuguese and English stay in scope, including the two live questions. Genuinely off-topic questions stay refused.
- DONE criterion: Quais foram minhas 3 maiores transações este mês? is in scope.
- DONE criterion: The unaccented form, the uppercase form, and Qual foi meu maior gasto? are in scope.
- DONE criterion: English questions about the user's own transactions, including the largest this month, are in scope.
- DONE criterion: A genuinely off-topic question, including an accented Portuguese one, stays out of scope.
- DONE criterion: Tests cover accented, unaccented, and uppercase variants in Portuguese and English.
- DONE criterion: The accent folding is documented in CHANGELOG Unreleased and the version in pyproject.toml stays 1.0.0.

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

Constraints: do not run the production migration; do not merge; code, tests, and docs stay in English.

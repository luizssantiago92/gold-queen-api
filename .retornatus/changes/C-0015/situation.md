<!-- retornatus-meta
{
  "change_id": "C-0015",
  "schema_version": 1
}
-->

# Situation

## Demand

The biggest-expense question waits on the model until it times out, then returns a generic unavailable reply.

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

- Demand stated: The biggest-expense question waits on the model until it times out, then returns a generic unavailable reply.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Qual foi meu maior gasto, and the same largest-expense questions, are answered from the selected transactions and do not call the model. A card-bill payment is still omitted. Other treasury questions still call the model.
- DONE criterion: Qual foi meu maior gasto returns the largest expense description and amount and does not call the model.
- DONE criterion: A BANK fatura payment is not named as that largest expense.
- DONE criterion: A repeated largest-expense question is served from cache and still does not call the model.
- DONE criterion: A treasury question that is not about the largest expense still calls the model.

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

Gemini uses a 30 second client timeout and a timeout is retried, so three attempts take about 90 seconds. Chat then returns the generic unavailable text and drops sources. The largest expense was already selected before that call.

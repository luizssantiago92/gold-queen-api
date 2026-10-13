<!-- retornatus-meta
{
  "change_id": "C-0014",
  "schema_version": 1
}
-->

# Situation

## Demand

The Queen chat answer and Queen's Tips must return the transactions that grounded the answer so the web can show them.

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

- Demand stated: The Queen chat answer and Queen's Tips must return the transactions that grounded the answer so the web can show them.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: POST /v1/chat/query and GET /v1/advisor/queen-tips return a sources list. Each item has id, date, description, amount, category, and account for a transaction placed in the grounding context for that answer. OpenAPI describes the schema. Off-topic refusals and failed model calls return an empty list. A card-bill settlement is not a source. The largest-expense question returns that expense.
- DONE criterion: Chat and Queen's Tips JSON include sources with id, date, description, amount, category, and account.
- DONE criterion: A question about the largest expense returns that expense transaction and omits a BANK fatura payment.
- DONE criterion: An off-topic refusal and a failed model call return an empty sources list.
- DONE criterion: The OpenAPI schema for the chat and queen-tips responses describes sources.

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

The model currently sees only month totals and category sums. The web cannot show which movements the answer used. Card-bill settlements stay out of expense context. Chat cache is still keyed by the question text.

## Reopened Situation

The fourth finish line must be proved by the test suite, so it names the response fields without calling the document a spec.

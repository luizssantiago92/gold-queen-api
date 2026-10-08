<!-- retornatus-meta
{
  "change_id": "C-0013",
  "schema_version": 1
}
-->

# Situation

## Demand

Demo expenses double-count a bank payment PAGAMENTO FATURA CARTAO VISA of -167.70 when that amount equals the Mastercard Black card purchases. Month totals, category split, the daily series, and the AI context add every negative amount. The payment must stay in the transaction feed, and card purchases must stay in expenses. Transaction grounding, timeouts, and quota consistency are out of scope.

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

- Demand stated: Demo expenses double-count a bank payment PAGAMENTO FATURA CARTAO VISA of -167.70 when that amount equals the Mastercard Black card purchases. Month totals, category split, the daily series, and the AI context add every negative amount. The payment must stay in the transaction feed, and card purchases must stay in expenses. Transaction grounding, timeouts, and quota consistency are out of scope.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: In treasury.py, leave a row out of month totals, the category split, the daily series, and the AI expense context only when the amount is negative, the account type is BANK, and the description matches fatura or pagamento fat. Card purchases stay in expenses. The payment stays in the transaction feed.
- DONE criterion: When a BANK payment of -167.70 matches fatura and the credit-card purchases sum to 167.70, month expenses equal 167.70.
- DONE criterion: The category split, the daily series, and the AI summary month expenses equal those purchases.
- DONE criterion: The payment remains listed in the transaction feed.
- DONE criterion: A negative purchase on a CREDIT account stays inside expenses.

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

Expense helpers sum every negative amount across BANK and CREDIT accounts. Display category labels a fatura row CreditCard but does not remove it from the total. The transaction feed reads every row. Card purchases on a CREDIT account must remain expenses.

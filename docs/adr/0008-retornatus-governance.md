# ADR 0008: Retornatus governs changes in this repository

- Status: Accepted
- Recorded: 2026-10-07 (the service already runs this way)

## Context

More than one agent edits this repository. A pull request needs a written finish line and evidence that can be re-checked, not only the conversation that produced the diff. The historical brief points at Retornatus for that governance. AI output validation stays in `app/core/ai_guardrails.py`; Retornatus does not replace it.

## Decision

`.retornatus/` is the canonical state: Changes, contracts, and evidence. Behavior changes are recorded there (C-0001 through C-0008, and this documentation change). `.github/workflows/retornatus.yml` runs on pull requests, executes `gate suppressions`, `verify`, and `gate scope`, and fails the job when the verdict is not `SATISFIED`.

`.retornatus/config.toml` (Retornatus 1.9.1) requires four executed checks: `uv run pytest -q`, `uv run ruff check app tests scripts alembic`, `uv run ruff format --check .`, and `uv run mypy`. A code diff with no touched Change fails the omission check. A Dependabot pull request that only bumps dependency manifests is warned instead, so the required check is not skipped for that author. The workflow token can read contents and, on the job, write a pull request comment. It does not push, merge, or deploy.

Git use follows the harness tiers: local commits are agent work, push and pull requests happen when asked, and merge, deploy, and release publication stay with the owner.

## Consequences

A governed pull request carries a Change whose contract matches the diff. Docs-only work still runs the same pytest, ruff, and mypy checks before Assurance is `SATISFIED`. Active rules are empty unless a human activates one. The CI workflow in `ci.yml` remains the test, lint, typecheck, and `pip-audit` source for GitHub; Retornatus does not replace it.

## Alternatives

Relying on CI alone would show that tests passed and would not record what "done" meant. Skipping the Change on a code diff fails `retornatus-gates`. Auto-activating rules from an agent lesson was not adopted; rule candidates stay a human decision.

<!-- SPEC-GUARDRAILS:BEGIN -->
# Execution Contract (Spec Guardrails)

When planning architecture, specs, or multi-step features, read the hub first:

- `.github/skills/agent-architecture.md` — SDD hub: contract, phases, gates, complexity router
- `.github/skills/references/` — phase procedures (explore, project-init, constitution, specify, discuss, design, tasks, analyze, implement, validate, converge, archive, memory, quick-mode, context-limits, lessons, sub-agents)
- `.github/skills/task-graph-engineering.md` — task DAG, parallelism, verify topology
- `.github/skills/engineering-standards.md` — secure coding, code quality, artifact language
- `.github/skills/security-review.md` — security checklist for /verify
- Sister skills (`appsec`, `qa-strategy`, `code-simplify`, `ship-ready`, `git-handoff`) — load **one conditional** at a time

Deterministic gates (`python3`, non-zero exit means STOP):

- Scripts in `.specs/guardrails/scripts/` — the **agent** runs them at phase boundaries (see hub).
- Humans: `install` once; optional `feature-init`, `project-init`, `doctor`, `classify-change`, `feature-status`, `feature-overview`.
- Full CLI: `npx @luizsantiago/spec-guardrails --help`
- Onboarding: `.specs/GETTING_STARTED.md`

All project artifacts are written in English.
Persistent state: `.specs/STATE.md`, `.specs/lessons.json`, `.specs/LESSONS.md`.
GitHub Copilot reads this file as repository custom instructions.
Cursor and Claude Code use their own adapter entry files — see Platform-parity.md in the package repo.
<!-- SPEC-GUARDRAILS:END -->

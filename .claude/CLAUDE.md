<!-- SPEC-GUARDRAILS:BEGIN -->
# Execution Contract (Spec Guardrails)

When planning architecture, specs, or multi-step features, read the hub first:

- `.claude/skills/agent-architecture.md` — SDD hub: contract, phases, gates, complexity router
- `.claude/skills/references/` — phase procedures (explore, project-init, constitution, specify, discuss, design, tasks, analyze, implement, validate, converge, archive, memory, quick-mode, context-limits, lessons, sub-agents)
- `.claude/skills/task-graph-engineering.md` — task DAG, parallelism, verify topology
- `.claude/skills/engineering-standards.md` — secure coding, code quality, artifact language
- `.claude/skills/security-review.md` — security checklist for /verify
- Sister skills (`appsec`, `qa-strategy`, `code-simplify`, `ship-ready`, `git-handoff`) — load **one conditional** at a time

Deterministic gates (`python3`, non-zero exit means STOP):

- Scripts in `.specs/guardrails/scripts/` — the **agent** runs them at phase boundaries (see hub).
- Humans: `install` once; optional `feature-init`, `project-init`, `doctor`, `classify-change`, `feature-status`, `feature-overview`.
- Full CLI: `npx @luizsantiago/spec-guardrails --help`
- Onboarding: `.specs/GETTING_STARTED.md`

All project artifacts are written in English.
Persistent state: `.specs/STATE.md`, `.specs/lessons.json`, `.specs/LESSONS.md`.
Cursor users also get `.cursorrules` + `.cursor/rules/engineering-baseline.mdc` — same contract, different entrypoint. See Platform-parity docs in the package repo.
<!-- SPEC-GUARDRAILS:END -->

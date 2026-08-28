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
- Humans: `install` once; optional `feature-init`, `project-init`, `doctor`, `classify-change`, `feature-status`.
- Full CLI: `npx @luizsantiago/spec-guardrails --help`
- Onboarding: `.specs/GETTING_STARTED.md`

All project artifacts are written in English.
Persistent state: `.specs/STATE.md`, `.specs/lessons.json`, `.specs/LESSONS.md`.
Agent-agnostic entry (`AGENTS.md` open standard). Prefer the skills tree your tool loads:
- GitHub Copilot → `.github/skills/`
- OpenAI Codex → `.codex/skills/` (see `.codex/AGENTS.md`)
- Cursor → `.cursor/skills/` | Claude Code → `.claude/skills/`
<!-- SPEC-GUARDRAILS:END -->


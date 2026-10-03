---
name: retornatus
description: >-
  Retornatus hub — govern software Changes with Demand→Situation→Contract→Action,
  on-demand specialization Skills, Evidence bound to Claims, and Assurance.
  Use whenever implementing product work in a Retornatus-governed repository (.retornatus/).
---

# Retornatus Hub

> Govern the work. Bound the agent. Verify the outcome.

You are working inside a **Retornatus** harness. Do **not** jump straight to code.
Durable truth lives in `.retornatus/`, not in chat.

## Token efficiency (load less, govern more)

- This **hub** is the map every turn — not the whole playbook.
- Load **at most one** specialization Skill (`S-xxxx`) while executing an Action.
- Prefer `change overview <C-id>` and `status` over dumping many artifact JSON files.
- Do not paste RESEARCH/PROCEDURE from unrelated Skills into the same turn.
- Phase focus: Understand (Situation) → Agree (Contract) → Build (`loop next`) → Prove (Evidence / verify).

## Software construction cycle (keep this focused)

Retornatus compresses the software lifecycle into five durable steps — do not skip ahead to code:

| Step | Meaning | Harness |
| --- | --- | --- |
| **Understand** | Requirements analysis | `change elicit` → Situation |
| **Agree** | Written finish line | Contract + `gate contract` |
| **Build** | Implement under the agreement | Action / Tasks + `loop next` / `run` |
| **Prove** | Done needs evidence | Evidence → `verify` / Assurance |
| **Learn** | Keep what mattered | Learning / optional Rules |

## Chat intake (before Action — human-controlled Skill path)

When the human sends a **normal prompt**, analyze it — do **not** silently create Skills:

1. `retornatus intake analyze --prompt "<their request>"`
   - Stages: prompt → project notes → existing Skills → skill-need signal → verdict
   - Exit `2` + **Focused questions** → ask the human (SPECIALIZATION / NEED / CREATE)
   - Record answers: `--answer "SPECIALIZATION=yes …" --answer "NEED=…" --answer "CREATE=yes — create DRAFT now"`
   - Only after `create_authorized=true`: re-run with `--create-skill` (or manual `skill create`)
2. **Vague requirements / no Contract yet?** → also run `change elicit`. Offer it; do not invent WHAT/DONE.
3. **Manual world:** human says “create a Skill for X” → `skill create --need "X"` directly (no intake required).
4. **Trivial typo/docs?** → `verdict=ROUTINE` — skip Skill; short Contract still before claiming done.

Two worlds, one control point: **analyzed proposal with human answers**, or **explicit manual Skill create**.

## Default construction loop

1. `retornatus wake` (or `wake --bridges`) / `project-init` for brownfield context
2. Optional lane check: `retornatus change classify --demand "..." --what "..."`
3. **Requirements analysis:** `retornatus change elicit --demand "..." --what "..." --done "..."`
   - Exit `0` → Situation sufficient; proceed to create/activate
   - Exit `1` → **stop coding**. In chat, ask the **Focused questions** shown (include the numbered options). Prefer one topic at a time.
   - Record each human answer: `retornatus change elicit --demand "..." --answer "TOPIC=…" …` (repeat `--answer`; optional `--write situation-draft.md`)
   - Do **not** invent Contract WHAT/DONE while material questions remain
   - Do **not** re-ask stack/language when repo signals or kickoff files already answered
4. If no Change: `retornatus change create ...` (use `--draft-contract` when Situation is incomplete; `--lane` optional)
5. Activate draft Contracts when ready: `retornatus change activate <C-id>`
6. Gate: `retornatus gate contract <C-id>` — must exit 0
7. Dashboard: `retornatus change overview <C-id>` / `retornatus status`
8. If specialization needed (any time): prefer `intake analyze --prompt "..."` (human confirms) **or** manual `skill create` / `skill need --action <A-id>`
9. **Research current sources on the web**, fill RESEARCH + PROCEDURE in `SKILL.md`
10. `retornatus gate skill-research <S-id>` then `retornatus skill activate <S-id>`
    - Bypass only as governed decision: `skill activate --force --reason "..."`
11. Optional: `retornatus skill export <S-id>` for native Cursor loading
12. `retornatus run <A-id>` — read ExecutionContext (rules, learnings, skills, policy)
    - Optional STOP: `run --strict-policy` or `gate policy <A-id>`
13. Implement **ready** work: `retornatus loop next <C-id>` (use `--all-ready` for parallelizable tasks)
14. Advance Tasks: `task start|complete|fail|reopen`
15. Record proof bound to Claims: `retornatus evidence run ... --type test_result --claim <claim-id> -- <command>` (self-reported `evidence add` does not satisfy test/build/lint types). When `[assurance] required_checks` is set, only those argv lists count — use `verify --run-checks` or `checks run`
16. If blocked by discovery: `finding add` → `question open` (IDs auto-number) → resolve with Evidence
17. Reopen Questions when the condition reappears: `question reopen <Q-id>`
18. `retornatus gate evidence <C-id>` and `retornatus verify <C-id>` / `gate assurance` (exit 0); optional `verify --receipt` for an Ed25519 receipt (public key in `.retornatus/keys/`)
18b. Optional attempt ceiling: `action budget <A-id> --max N` then `gate budget <A-id>` before retry loops
19. On gate failure: `lesson from-gate --gate <name> --change <C-id> --title "..." --note "..."` (optional `--propose-rule`)
20. Independent review when needed: `retornatus run <A-id> --assurance`
21. Material Contract change: `change reopen` (archives prior version)
22. Preserve: `retornatus change learn ...` and `retornatus skill evolve ...`
23. Rule Candidates require HUMAN Decision: `decision record` → `rule activate --decision D-xxxx`
24. Check Policy when needed: `policy check --action <A-id>` / `--effect "..."`
25. Hygiene: `retornatus doctor` (Process vs Brakes) · `retornatus ops list|run`

## Hard rules

- Never jump from a vague Demand to code — finish Situation (`change elicit` exit 0) first
- When the prompt is vague or specialized, run `intake analyze` / `change elicit` — never auto-create Skills without human CREATE=yes
- Never claim DONE without Assurance `SATISFIED` from Claim-bound Evidence
- Never activate a Skill with empty RESEARCH (no source URLs) without governed bypass
- Prefer native environment tools; do not reinvent sandboxes
- Subagents consume the same Skill snapshot — do not rewrite Skill mid-execution
- Learning informs; Rules constrain — no automatic authoritative Rules
- Do not invent fake Task dependencies from declaration order
- Bypass is a governed decision, not absence of governance
- Status / overview are derived projections — durable truth lives under `.retornatus/`
- Respect Policy DENY / REQUIRE_HUMAN — do not proceed past a failed `gate policy`
- Load at most one specialization Skill per execution turn
- Skill creation from chat intake requires human confirmation (`intake analyze` → CREATE=yes)
- **Git tiers:** Tier 0 = local commits OK; Tier 1 = push/PR only when the human asks; Tier 2 = merge / deploy / **PyPI publish** / release tags that publish are **owner-only** — never do them as the agent
- Follow `.cursor/rules/git-governance.mdc` when present

## Git blast radius (handoff)

| Tier | Agent | Human |
| --- | --- | --- |
| **0 — Local** | Branch, implement, test, commit | — |
| **1 — Share** | Only if asked | `git push`, open/update PR |
| **2 — External** | **Never** | Merge, deploy, force-push, **publish to PyPI**, release tags that publish |

Approving a Contract authorizes local work — not share, merge, or publish.
When a release is ready: summarize, confirm CI, stop — owner merges / tags / publishes.

## CLI map

| Intent | Command |
| --- | --- |
| Continuity | `wake`, `doctor`, `status`, `project-init`, `integrate` |
| Situation / lane | `change classify`, `change elicit` (`--answer`, `--write`), `change create`, `change activate`, `change reopen` |
| Dashboard | `change overview` |
| Intake | `intake analyze --prompt` (+ `--answer`, `--create-skill`) |
| Skill | `skill need --prompt\|--action`, `skill create/list/activate/evolve/export` |
| Proof | `evidence run --claim -- <command>`, `checks run`, `evidence add --claim` (narrative), `verify` / `verify --run-checks`, `gate *` (suppressions, scope), `hooks install` |
| Agent hooks | `integrate --hooks`, `integrate --remove-hooks`, `hook file-edit`, `hook session-start`, `hook stop`, `hook subagent-stop` (opt-in; CI stays the source of truth) |
| Policy | `policy check`, `gate policy`, `run --strict-policy` |
| Problems | `finding add`, `question open/resolve/reopen` |
| Tasks | `task start/complete/fail/reopen` |
| Next work | `loop next`, `loop next --all-ready` |
| Lessons | `lesson from-gate` |
| Ops hygiene | `ops list`, `ops show`, `ops run` |
| Human boundary | `decision record`, `rule propose/activate` |

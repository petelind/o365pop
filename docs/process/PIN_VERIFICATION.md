# PIN verification — Edda v73 re-run (in-flight)

**Workflow:** Plan Iteration (PIN-01 → PIN-05)
**Playbook:** Edda v73.0
**Date:** 2026-09-05
**Goal sentence:** Ship the Entourage↔Microsoft 365 mail bridge (act-1-bridge / BOOT through DEP)

This is a **reconcile**, not a second iteration. Branch `iteration/20260905-mail-bridge` and Milestone **#1** already exist. PIN-03 did not re-skeleton implemented scenarios. PIN-04 did not mint duplicate issues.

---

## PIN-01 Readiness Check

| Gate | Result |
|------|--------|
| 1 BSP | PASS — `Makefile`, `requirements.txt` |
| 2 User journey | PASS — Act 1–4 in `docs/features/user_journey.md` |
| 3 Feature specs | PASS — 6 files in `docs/features/act-1-bridge/` |
| 4 SAO.md | PASS |
| 5 AI IDE | PASS — Cursor ADE `.cursor/rules/_ai-context.mdc` + `min-iteration.mdc` (stock PIN checks `CLAUDE.md`; DSP-04 Cursor substitute) |
| 6 Agent harness | SKIP — `agent_harness: n/a` (SAO §17) |

Mockups: none. Advisory skip — SAO §1 has no UI. Feature specs only.

**Output:** `target_act=act-1-bridge`; feature files listed in `docs/plans/iterations/pin-orient-20260905.md`.

## PIN-02 Orient & Validate Scope

Wrote `docs/plans/iterations/pin-orient-20260905.md` (v73 filename; prior `pit-orient-20260905.md` is the FeatureFactory draft).

- First iteration: no `ITER-*.md` lessons
- All 7 scenarios stay in scope (`scope_override: confirmed`)
- Deferred: none

## PIN-03 Contract

| PIN-03 step | This re-run |
|-------------|-------------|
| Create branch | Already on `iteration/20260905-mail-bridge` |
| BPE-01 per scenario | Existing `docs/plans/*_IMPLEMENTATION_PLAN.md` — not rewritten |
| Skeletons | Already committed S1–S7; **not** re-committed |
| Checkpoint verify | S1–S4 green (closed). S5 checkpoint red until SEND. S6–S7 NIE (expected) |
| Conflict map | Unchanged — serialized A→G |
| Manifest | Reconciled: `milestone_number`, `feature_file_paths`, `system_dependencies`, log-story fields |

System dependencies: `[]` for all seven (FileGraphAdapter / eager Celery; Redis is BSP, not a PIN stub).

## PIN-04 Publish

Platform: **GitHub** (`petelind/o365pop`).

| Artifact | Action |
|----------|--------|
| Milestone #1 | Exists — description refreshed with reconciled MANIFEST |
| Issues #1–#7 | Exist — **no new issues** |
| Labels | Already bootstrapped (`status-*`, `parallel-group-*`) |

`milestone_number: 1` (integer, not null).

## PIN-05 Human Acceptance

PIN-05 protocol sections live in `.cursor/rules/min-iteration.mdc` (Edda v73 TL / dr-dobbs / Saga). Stock PIN-05 names `CLAUDE.md`; DSP-04 Cursor does not generate that file.

**STOP — waiting for explicit human GO.**

Activate MIN with: `Work on Milestone #1`

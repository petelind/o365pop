## Orient Summary — 2026-09-05

### Input Scope

Goal: Ship the Entourage↔Microsoft 365 mail bridge (BOOT through DEP) on LibreELEC in one iteration.

Selected scenarios (no GitHub issues yet — PIN-01 issue-number entry criterion waived; PIN-03 will mint issues after a remote exists):

| ID | Feature | Plan | Notes |
|---|---|---|---|
| S1 | BOOT | BOOT_IMPLEMENTATION_PLAN.md | Already implemented on `main` (package, sqlite, Celery, logging, TFK) |
| S2 | AUTH AUTH1.1–1.3 | AUTH_IMPLEMENTATION_PLAN.md | |
| S3 | SYNC SYNC1.1–1.3 | SYNC_IMPLEMENTATION_PLAN.md | |
| S4 | POP POP1.1–1.3 | POP_IMPLEMENTATION_PLAN.md | |
| S5 | SMTP SMTP1.1 + SEND1.1–1.2 | SMTP_IMPLEMENTATION_PLAN.md | |
| S6 | TEAM TEAM1.1–1.4 | TEAM_IMPLEMENTATION_PLAN.md | |
| S7 | DEP DEP1.1 | DEP_IMPLEMENTATION_PLAN.md | |

### Velocity Trend

Last 3 ratios: n/a, n/a, n/a — first iteration (no history).

### Dominant Drift

None (0/0 iterations)

### Footprint Accuracy

n/a — first iteration

### Scope Validation

First iteration — no historical patterns.

**Scope risk (human-directed):** all remaining product features in one iteration. Acceptable because BPE-01 plans already exist, BOOT is green, and the critical path is strictly serialized (AUTH → SYNC → POP/SMTP → TEAM → DEP). No parallel MIT workers until footprints are proven disjoint.

**PIN-01 discrepancy:** human provided a goal sentence but not GitHub issue numbers. No `origin` remote; `gh issue list` cannot run. Proceeding with S1–S7 as the selected backlog so Contract can run locally.

### Watch For

- None from history — first iteration
- Shared files (`sync/tasks.py`, `graph/`, `tosser/outbound_scanner.py`, `config.py`) — serialize, do not parallel
- Do not re-open BOOT except for DEP bind helpers

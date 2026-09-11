# TASK — Change Reconciliation

**Feature**: Entourage Tasks two-way sync (To Do lists, Outlook categories)
**Produced by**: BPE-08 Process Change Request
**Date**: 2026-09-11
**Status**: Specs updated in place. BPE-01 plan: `docs/plans/TASK_IMPLEMENTATION_PLAN.md` (awaiting approval / issue handoff).

## Trigger

POP cannot populate Entourage Tasks. Flag headers are ignored. A `.ics` attachment works only after open-and-save.

Pilots on `Deniss-MacBook-Pro-2.local` (macOS 10.14.6, Office 2008, Python 3.13): `subprocess` + `osascript` created real Entourage Tasks (`make new task`). AppleScript can read `id`, `name`, `completed`, `due date`, `content`, `modification date`.

Operator CR (this conversation):

1. A service runs on LibreELEC (the o365pop Graph proxy).
2. A service runs on the Entourage Mac.
3. Every minute the Mac pulls tasks from the proxy and syncs them (two-way task fields as already discussed), including category and task list.
4. Microsoft To Do **task list** ↔ Entourage **Project** (create if missing; delete if the list is gone; rename if the list name changed).
5. Outlook **categories and colors** ↔ Entourage **categories** (map O365 category color → Entourage category color).
6. If LibreELEC is down, Mac `taskd` keeps trying quietly — no raise, no exit, no traceback (TASK1.8 / Q14).

## Reconciliation matrix

No GUI Screen IDs. Traceability IDs: **TASK1.1–TASK1.8** (Act 5). Mockups N/A (SAO §1 UI: None).

| Layer | Source | Current state (before) | Drift? | Notes |
|---|---|---|---|---|
| User journey | `docs/features/user_journey.md` | Acts 1–4 mail/Teams only | Y | Add Act 5 |
| Scenarios | `docs/features/act-1-bridge/*.feature` | AUTH/SYNC/POP/SMTP/TEAM/DEP | Y | New `tasks.feature` |
| Mockups | HTML | Absent | N | N/A this stack |
| Screen flow | `docs/ux/dialogue-map.md` | Acts 1–4 mermaid | Y | Add Act 5 subgraph |
| IA guidelines | `docs/ux/IA_guidelines.md` | CLI + POP/SMTP only | Y | Tasks surface + Mac agent |
| Prior plan | `docs/plans/O365POP_IMPLEMENTATION_PLAN.md` | BOOT–DEP | Y | Index row 7 TASK; no BPE-01 body yet |
| Architecture | `docs/architecture/SAO.md` | Mail/Teams Graph only | Y | Snapshot + Mac `taskd`; scopes; data |
| As-built | `o365pop/`, tests | No task snapshot, no Mac agent | Y | Intentional — BPE-08 does not code |
| Clarifications | `docs/plans/O365POP_Clarifications.md` | Q1–Q8 | Y | Q9–Q13 |
| Phrase catalog | `docs/features/CATALOG.md` | AUTH–DEP | Y | TASK rows (pytest later) |
| Fixture catalog | `tests/fixtures/CATALOG.md` | SYNC mail cases | Y | TASK Graph snapshot cases (later) |
| ADE map | `.cursor/rules/_ai-context.mdc` | Mail-only architecture sketch | Y | Second hop |
| Stack locks | `.cursor/rules/o365pop-stack-locks.mdc` | popd/smtpd vs Graph | Y | Mac agent vs Graph / Database |

## Locked target state

```
Graph To Do + masterCategories
        ↑ GET/PATCH
LibreELEC o365pop (Celery)  — writes /storage/o365pop/tasks/snapshot.json
        ↑ pull every 60s (LAN or WG file copy; no Graph on the Mac)
Mac taskd (Python 3.13 stdlib + osascript)
        ↔ Apple Events
Entourage 2008 Tasks / Projects / Categories
```

- **LibreELEC** remains the only Graph client. Tokens stay there. New scopes: `Tasks.ReadWrite`, `MailboxSettings.Read` (plus existing mail/chat). Operator re-runs `make login`.
- **Mac `taskd`** never calls Graph, never writes Entourage’s `Database` file, never speaks POP/SMTP. Injection is Apple Events only (`osascript` from Python).
- **Interchange** is an atomic JSON snapshot + receipt files under `/storage/o365pop/tasks/` (not POP, not `.ics` in Inbox, not an HTTP app).
- **Task list** (`GET /me/todo/lists`) ↔ Entourage **Project**, joined by Graph list id stored in the Project (notes or equivalent). Create / rename (name only) / delete as the operator specified.
- **Category catalog** (`GET /me/outlook/masterCategories`) ↔ Entourage **category**, joined by Graph category id. Create if missing; rename with `displayName`; set color from Graph `color` (preset) via the Entourage palette map. Delete only categories **this sync created**. Do not delete Entourage’s built-in categories (Family, Friends, …) if they have no Graph id.
- **Task fields (two-way)**: title, due, completed, list→project, category names. Join key: `o365pop-uid:` in Entourage task `content` (Graph todoTask id). Last write wins using Entourage `modification date` vs Graph `lastModifiedDateTime`.
- **Local Entourage tasks** without `o365pop-uid:` stay local (no Graph create).
- **Deletes of tasks**: Graph delete → delete the uid-tagged Entourage task. Entourage delete → Graph delete of that uid (unlike POP DELE / Q3). Lists/projects follow the operator’s delete rule above.
- **POP path abandoned for Tasks.** Flag headers and `.ics` attachments are not the Tasks product.
- **LibreELEC down:** `taskd` stays up. WARNING `reachability=down`, Entourage unchanged, receipts queued, retry every 60s. No exceptions to the operator.

## Proposed spec diffs (applied)

| File | Change |
|---|---|
| `docs/plans/TASK_CHANGE_RECONCILIATION.md` | This record |
| `docs/architecture/SAO.md` | Blocks, Graph, data, infra, scopes, Task hop |
| `docs/features/user_journey.md` | Act 5 |
| `docs/features/act-1-bridge/tasks.feature` | TASK1.1–1.7 |
| `docs/ux/dialogue-map.md` | Act 5 |
| `docs/ux/IA_guidelines.md` | Tasks + Mac agent |
| `docs/plans/O365POP_Clarifications.md` | Q9–Q13 |
| `docs/plans/O365POP_IMPLEMENTATION_PLAN.md` | Row 7 placeholder |
| `docs/features/CATALOG.md` | TASK phrases |
| `tests/fixtures/CATALOG.md` | TASK fixtures (land with BPE-01) |
| `.cursor/rules/_ai-context.mdc` | Architecture sketch |
| `.cursor/rules/o365pop-stack-locks.mdc` | Mac agent locks |

**Not in this activity:** `TASK_IMPLEMENTATION_PLAN.md`, code, tests, Azure app-registration change (human).

## Open questions (locked defaults)

| # | Question | Locked unless operator overrides |
|---|---|---|
| Q9 | How do tasks reach Entourage? | Mac `taskd` + snapshot files. Not POP. |
| Q10 | Task list mapping? | To Do list ↔ Project; create / rename / delete. |
| Q11 | Categories? | Outlook `masterCategories` ↔ Entourage category + color map; task.categories[] applied on the task. |
| Q12 | Two-way? | Yes for title/due/completed (and task delete). Graph owns list and category **catalog**. |
| Q13 | Color table? | Map Graph `preset0`–`preset24` onto Entourage’s category colors (nearest). Exact enum table is a BPE-01 fixture on the 10.14 Entourage dictionary — do not invent RGB in code until that probe lands. |
| Q14 | LibreELEC down? | `taskd` never raises/exits; WARNING + retry next tick. |

## Fast path?

No. New Act, new Graph resources, new process on the Mac.

## Gate

Operator stated the five CR bullets and asked to document per BPE-08 and update SAO. Specs updated in the same pass. **BPE-01 Plan Feature** is the next activity when they say to implement.

# TASK — Implementation Plan

**Feature**: TASK Entourage Tasks sync with Microsoft To Do
**Feature File**: `docs/features/act-1-bridge/tasks.feature`
**Scenarios**: TASK1.1–TASK1.8
**GitHub Issues**: [#9](https://github.com/petelind/o365pop/issues/9)
**Branch**: `feature/entourage-tasks`
**Agent**: Dr. Dobbs v2
**Prerequisites**: AUTH (bearer) + DEP volumes. Mail/POP/SMTP/TEAM stay unchanged.
**CR**: `docs/plans/TASK_CHANGE_RECONCILIATION.md`

BPE-01 adjustments: no Django/HTMX. Mac `osascript` is **not** in CI — `FakeEntourage` is the FileGraphAdapter analog. `deploy/entourage/` is stdlib-only and must not import `o365pop.graph`.

---

## Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/features/act-1-bridge/tasks.feature` | 1–65 | TASK1.1–1.8 |
| `docs/architecture/SAO.md` | §2 Tasks ↔ Entourage | Snapshot hop, list→Project, category colors |
| `o365pop/graph/port.py` | 8–48 | **Extend GraphPort** — do not add a second client |
| `o365pop/graph/file_adapter.py` | 13–81 | Same fixture shape (`{value:[]}`); add todos/categories JSON |
| `o365pop/sync/tasks.py` | 33–66 | **Add** `sync_tasks`; do not fold into `sync_mailbox` |
| `o365pop/celery_app.py` | 41–50 | Add beat `sync-tasks` (`TASK_SNAPSHOT_SECONDS`, default 60) |

MCP / SAO §17 / §18: **N/A** — no rows.

---

## Do Not Do

- Do NOT call Graph from `deploy/entourage/` or from `popd` / `smtpd`
- Do NOT import `o365pop.graph` / `o365pop.sync` on the Mac
- Do NOT write Entourage’s `Database` file
- Do NOT mint Tasks as RFC822 / POP / `.ics` Inbox mail
- Do NOT add an HTTP app for the snapshot (path/mount/rsync only)
- Do NOT fold task publish into `sync_mailbox`
- Do NOT add SQLite tables for task joins (Mac `uid_map.json` only)
- Do NOT delete Entourage categories this sync did not create
- Do NOT treat Outlook calendars as Project joins (CAL Q15 C)
- Do NOT raise or `sys.exit` when LibreELEC is unreachable (TASK1.8)
- Do NOT mock GraphPort or EntouragePort in integration tests — FileGraphAdapter + FakeEntourage
- Do NOT run `osascript` in `make test`

---

## SAO.md Sections That Apply

- Design Principles 1, 5, 7 — daemon/Graph split; Mac never Graph
- §1 Application Blocks — `taskd` row
- §2 Tasks ↔ Entourage (not POP) — mapping table
- §4 Data Architecture — `tasks/snapshot.json` + receipts
- §5 Test Strategy — FakeEntourage / FileGraphAdapter; osascript not CI
- §7 Error Handling — TASK1.8 quiet retry
- §8 / §12 — `TASK_SNAPSHOT_SECONDS`, `/storage/o365pop/tasks`
- §11 Observability — log story
- §13 Security — no tokens on the Mac

---

## Current State Assessment

**Exists:** GraphPort + File/Http adapters (mail/chat only); Celery `sync_mailbox` / `scan_outbound_spool`; scopes without Tasks; AppleScript pilot on `Deniss-MacBook-Pro-2.local` (`make new task` works).

**Missing:** To Do / masterCategories on GraphPort; snapshot writer; `sync_tasks` beat; `deploy/entourage/` apply loop; FakeEntourage; color map; receipts.

---

## Clarifications (locked)

Q9–Q14 in `docs/plans/O365POP_Clarifications.md`. Extra implementor locks:

| Topic | Lock |
|---|---|
| Transport | `taskd` reads `TASK_SNAPSHOT_PATH` (file). Operator mounts or rsyncs. Missing/unreadable path = TASK1.8. No SSH inside `taskd` v1. |
| Join store | Mac `uid_map.json` next to `taskd` (task uid → Entourage id, list id → Project id, category id → Entourage category id). No new SQLite. |
| Celery | New task `o365pop.sync.sync_tasks`: publish snapshot **then** apply receipts. |
| Entourage in CI | `FakeEntourage` in-memory port. Live `osascript` is operator smoke only. |
| Color map v1 | Table below. If live Entourage rejects a color name, fix the table in the same slice. |

**Starter color map** (Graph `outlookCategory.color` → Entourage `category color` name; adjust after live probe):

| Graph | Entourage |
|---|---|
| `none`, `preset12`, `preset13`, `preset14` | `gray` |
| `preset0`, `preset15` | `red` |
| `preset1`, `preset16` | `orange` |
| `preset2`, `preset17` | `maroon` |
| `preset3`, `preset18` | `yellow` (or `lime` if yellow missing) |
| `preset4`, `preset19` | `green` |
| `preset5`, `preset20` | `steel` |
| `preset6`, `preset21` | `olive` / `lime` |
| `preset7`, `preset22` | `blue` |
| `preset8`, `preset23` | `purple` |
| `preset9`, `preset10`, `preset11`, `preset24` | `cranberry` / `steel` / `maroon` as nearest |

Unknown preset → `gray`. Log `branch` `color_fallback=true`.

**Operator (human, not a code slice):** Azure app adds `Tasks.ReadWrite` + `MailboxSettings.Read`; `make login` again.

---

## Snapshot / receipt contract

Atomic write: `snapshot.json.tmp` → replace `snapshot.json`.

```json
{
  "generated_at": "2026-09-11T16:00:00Z",
  "lists": [{"id": "list-work", "displayName": "Work"}],
  "categories": [{"id": "cat-red", "displayName": "Urgent", "color": "preset1"}],
  "tasks": [{
    "id": "task-q3",
    "listId": "list-work",
    "title": "File the Q3 report",
    "dueDateTime": "2026-09-12T21:00:00Z",
    "status": "notStarted",
    "categories": ["Work"],
    "lastModifiedDateTime": "2026-09-11T15:00:00Z"
  }]
}
```

Receipt (`tasks/receipts/new/{uid}.json`):

```json
{
  "uid": "task-q3",
  "listId": "list-work",
  "title": "File the Q3 report",
  "dueDateTime": "2026-09-12T21:00:00Z",
  "status": "completed",
  "deleted": false,
  "modifiedAt": "2026-09-11T16:10:00Z"
}
```

LibreELEC moves applied receipts to `receipts/sent/`, failed after N tries to `receipts/failed/`.

---

## MCP Tools to Expose

Not applicable (no SAO §18).

---

## Agent Proof Table

Not applicable (SAO §17 N/A).

---

## Log Story Script

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `tosser.task_snapshot.publish` | entry | Celery publish | lists= tasks= |
| `tosser.task_snapshot.publish` | exit | snapshot written | path= bytes= |
| `sync.tasks.sync_tasks` | exit | publish+apply | published=1 patched= |
| `sync.tasks.sync_tasks` | error | Graph auth fail | reason=auth_failed |
| `taskd.pull` | branch | path missing / timeout / refused | reachability=down |
| `taskd.pull` | exit | snapshot read | lists= tasks= |
| `taskd.apply` | processing | create task | uid= |
| `taskd.apply` | exit | apply done | created= updated= |
| `taskd.apply` | branch | no o365pop-uid | skipped_local= |
| `taskd.receipts` | exit | receipt queued | uid= status= |

Never log tokens, mailbox passwords, or raw snapshot bodies (counts and ids only).

---

## Tests to Create

| Test | Level | Proves |
|---|---|---|
| `tests/unit/test_task_snapshot_parse.py` | unit | Valid snapshot dict; reject missing `id` |
| `tests/unit/test_task_category_color.py` | unit | TASK1.5 map; unknown preset → gray + fallback |
| `tests/unit/test_taskd_reachability_down.py` | unit | TASK1.8: no raise; WARNING `reachability=down`; Entourage untouched |
| `tests/unit/test_task_project_map.py` | unit | TASK1.2 create, 1.3 rename, 1.4 delete joined Project when the list is gone |
| `tests/unit/test_task_receipt_ignore_local.py` | unit | TASK1.7: no receipt for untagged task |
| `tests/unit/test_task_snapshot_log_story_happy.py` | unit caplog | publish entry/exit |
| `tests/unit/test_taskd_log_story_reject.py` | unit caplog | pull branch reachability=down |
| `tests/integration/test_publish_task_snapshot.py` | integration | FileGraphAdapter → atomic `snapshot.json` |
| `tests/integration/test_task_snapshot_create.py` | integration | TASK1.1 FakeEntourage: title, due, uid, Project, category |
| `tests/integration/test_task_receipt_patch.py` | integration | TASK1.6 receipt → `patch_todo_task` status=completed; FileGraphAdapter records PATCH |
| `tests/integration/test_sync_tasks_log_story_happy.py` | integration caplog | `sync_tasks` exit published= patched= |
| `tests/unit/test_celery_app.py` | extend | beat key `sync-tasks` schedule 60 |

`FakeEntourage` lives in `tests/support/fake_entourage.py`. It implements `EntouragePort` for real. Do not `unittest.mock` it.

---

## Implementation Plan

Rules: `do-skeletons-first`, `do-test-first`, `do-assert-log-story`, `do-not-mock-in-integration-tests`, `do-write-concise-methods`, `do-docstring-format`

### TASK0 Handoff (after approval only)

- [x] GitHub issue #9 with sections A–G + Lessons Learned inline
- [x] Index issue number
- [x] Commit `docs(plan): TASK Entourage sync plan Refs #9` (`ad37d4a`)
- [x] `gh issue comment` with SHA + slice order

### TASK1.8 + contracts (slice 1)

- [x] **1.1** Skeleton `deploy/entourage/{snapshot.py,color_map.py,taskd.py}` + `EntouragePort`
- [x] **1.2** `tests/support/fake_entourage.py`
- [x] **1.3** Red/green: parse, color map, reachability (no raise)
- [x] **1.4** Log story reject `taskd.pull` `reachability=down`
- **Commit**: `feat(taskd): parse snapshot and survive unreachable proxy`

### Graph + publish (slice 2) — TASK snapshot producer

- [x] **2.1** GraphPort: `list_todo_lists`, `list_todo_tasks`, `list_master_categories`, `patch_todo_task`, `delete_todo_task`
- [x] **2.2** FileGraphAdapter + HttpGraphAdapter; fixtures `tests/fixtures/graph/TASK1.1-q3-report/` (`lists.json`, `tasks.json`, `categories.json`)
- [x] **2.3** `tosser.task_snapshot.publish` atomic write
- [x] **2.4** `sync_tasks` Celery + beat; `TASK_SNAPSHOT_SECONDS`; `.env.example`; `Settings`
- [x] **2.5** Red/green: `test_publish_task_snapshot` + publish log story
- **Commit**: `feat(sync): publish To Do snapshot for Mac taskd`

### TASK1.2–1.4 Projects (slice 3)

- [x] **3.1** `deploy/entourage/apply.py` list↔Project on FakeEntourage
- [x] **3.2** Red/green: `test_task_project_map`
- **Commit**: `feat(taskd): sync To Do lists to Entourage Projects`

### TASK1.5 Categories (slice 4)

- [x] **4.1** Create/rename/color Entourage category; do not delete built-ins
- [x] **4.2** Red/green: `test_task_category_color`
- **Commit**: `feat(taskd): map Outlook category colors`

### TASK1.1 Tasks inbound (slice 5)

- [x] **5.1** Create/update FakeEntourage task: title, due, `o365pop-uid:`, Project, categories
- [x] **5.2** Red/green: `test_task_snapshot_create` + apply log story
- **Commit**: `feat(taskd): apply snapshot tasks into Entourage`

### TASK1.6–1.7 Receipts (slice 6)

- [x] **6.1** Queue receipt JSON; skip untagged (1.7)
- [x] **6.2** `tosser.task_snapshot.apply_receipts` → Graph PATCH/DELETE
- [x] **6.3** Red/green: `test_task_receipt_patch`, `test_task_receipt_ignore_local`, `test_sync_tasks_log_story_happy`
- **Commit**: `feat(sync): apply Entourage task receipts to Graph`

### Deploy + live smoke (slice 7)

- [x] **7.1** `deploy/entourage/README.md` + launchd plist (`StartInterval` 60)
- [x] **7.2** `OsascriptEntourage` adapter (not imported by `make test`)
- [ ] **7.3** Operator: new scopes + login; `taskd` on `Deniss-MacBook-Pro-2.local` against a Task1.1 fixture or live list
- **Commit**: `docs(taskd): launchd install notes`

**Checkpoint**:
`pytest tests/unit/test_task_snapshot_parse.py tests/unit/test_task_category_color.py tests/unit/test_taskd_reachability_down.py tests/unit/test_task_project_map.py tests/unit/test_task_receipt_ignore_local.py tests/unit/test_task_snapshot_log_story_happy.py tests/unit/test_taskd_log_story_reject.py tests/unit/test_celery_app.py tests/integration/test_publish_task_snapshot.py tests/integration/test_task_snapshot_create.py tests/integration/test_task_receipt_patch.py tests/integration/test_sync_tasks_log_story_happy.py -x`

---

## Definition of Done

- [x] Checkpoint green (includes log-story tests)
- [x] `make test` still green (mail/TEAM/DEP)
- [x] No `osascript` in merge-gate tests
- [x] Azure scopes documented; human login is operator DoD, not CI
- [ ] Operator 7.3: Azure `Tasks.ReadWrite` + `MailboxSettings.Read`, `make login`, live `taskd` on the Entourage Mac

---

## Lessons Learned

Planning this without Entourage in CI is the same split as Graph: a real in-memory port (`FakeEntourage`), not mocks. The color enum is the one leftover unknown — the starter table will be wrong until the first `osascript` on 10.14; that is a data fix, not a new SAO decision. Folding tasks into `sync_mailbox` would couple mail auth-fail (no retry) to a 60s task tick; a separate `sync_tasks` beat keeps TASK1.8 and mail sessions from sharing one failure bucket.

---

## Approval

Approve this plan to: open GitHub issue #N, commit `docs(plan): … Refs #N`, then execute slice 1. Do not implement before that handoff.

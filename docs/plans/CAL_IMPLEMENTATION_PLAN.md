# CAL — Implementation Plan

**Feature**: CAL Entourage Calendar sync with Outlook
**Feature File**: `docs/features/act-1-bridge/calendar.feature`
**Scenarios**: CAL1.1–CAL1.9
**GitHub Issues**: [#10](https://github.com/petelind/o365pop/issues/10)
**Branch**: `feature/entourage-calendar`
**Agent**: Dr. Dobbs v2
**Prerequisites**: AUTH (bearer) + TASK hop green. Mail/POP/SMTP/TEAM unchanged.
**CR**: `docs/plans/CAL_CHANGE_RECONCILIATION.md`

BPE-01 adjustments: no Django/HTMX. Mac `osascript` is **not** in CI — extend `FakeEntourage`. `deploy/entourage/` is stdlib-only and must not import `o365pop.graph`.

---

## Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/features/act-1-bridge/calendar.feature` | 1–90 | CAL1.1–1.9 |
| `docs/architecture/SAO.md` | §2 Calendar ↔ Entourage | Snapshot hop, Q15 B, attachments |
| `o365pop/graph/port.py` | 8–90 | **Extend GraphPort** — calendar methods |
| `o365pop/graph/file_adapter.py` | 83–136 | Same fixture shape; add calendars/events JSON |
| `o365pop/sync/tasks.py` | 57–104 | **Add** `sync_calendar`; do not fold into `sync_tasks` |
| `o365pop/celery_app.py` | 41–54 | Add beat `sync-calendar` (`CAL_SNAPSHOT_SECONDS`, default 60) |
| `deploy/entourage/apply.py` | 125–141 | `_delete_missing_projects` must honor calendar joins |
| `deploy/entourage/taskd.py` | 18–58 | Second snapshot path, same reachability |

MCP / SAO §17 / §18: **N/A** — no rows.

---

## Do Not Do

- Do NOT call Graph from `deploy/entourage/` or from `popd` / `smtpd`
- Do NOT import `o365pop.graph` / `o365pop.sync` on the Mac
- Do NOT write Entourage’s `Database` file
- Do NOT mint Calendar as RFC822 / POP / `.ics` Inbox mail
- Do NOT add an HTTP app for the snapshot (path/mount/rsync only)
- Do NOT fold calendar publish into `sync_mailbox` or `sync_tasks`
- Do NOT add SQLite tables for calendar joins (Mac `uid_map.json` only)
- Do NOT create/rename/delete the category **catalog** from calendar apply (CAL1.5)
- Do NOT set Entourage `to recipients` or PATCH Graph `attendees` (Q16)
- Do NOT sync shared / group / room calendars (Q18)
- Do NOT embed attachment bytes as base64 in `snapshot.json` (Q20)
- Do NOT delete a Project that still has a To Do **or** calendar join (Q15 B)
- Do NOT raise or `sys.exit` when LibreELEC is unreachable (CAL1.8)
- Do NOT mock GraphPort or EntouragePort in integration tests — FileGraphAdapter + FakeEntourage
- Do NOT run `osascript` in `make test`

---

## SAO.md Sections That Apply

- Design Principles 1, 5, 7 — daemon/Graph split; Mac never Graph; events not POP
- §1 Application Blocks — `taskd` pulls task + calendar snapshots
- §2 Calendar ↔ Entourage (not POP) — mapping table
- §4 Data Architecture — `calendar/snapshot.json` + receipts + attachments
- §5 Test Strategy — FakeEntourage / FileGraphAdapter; osascript not CI
- §7 Error Handling — CAL1.8 quiet retry
- §8 / §12 — `CAL_SNAPSHOT_SECONDS`, window env, `/storage/o365pop/calendar`
- §11 Observability — log story
- §13 Security — no tokens on the Mac

---

## Current State Assessment

**Exists:** TASK snapshot hop (GraphPort To Do, `sync_tasks`, `taskd`, FakeEntourage tasks/projects/categories).

**Missing:** Graph calendar methods; `calendar_snapshot` publisher; `sync_calendar` beat; Entourage event apply/receipts/acks; `Calendars.ReadWrite` scope; Settings `cal_*` fields; shared Project delete guard for calendar joins.

---

## Clarifications (locked)

Q15–Q20 in `docs/plans/O365POP_Clarifications.md`. Extra implementor locks:

| Topic | Lock |
|---|---|
| One tick | `__main__.py` runs TASK then CAL; missing path is WARNING only for that hop |
| Join store | `uid_map.json` gains `calendars` + `events`; Project delete skips if id in `lists` **or** `calendars` values |
| calendarView | −30 / +180 days (`CAL_WINDOW_PAST_DAYS`, `CAL_WINDOW_FUTURE_DAYS`); join occurrence id |
| Create acks | POST receipt + `calendar/acks/{localKey}.json`; next tick stamps `o365pop-uid:` |
| Attendees | Text in `content` (`o365pop-attendees:`); never `to recipients` |
| Q20 tokens | Starter: reminder minutes, show-as, sensitivity; fix table on live probe |
| Attachments | Files under `calendar/attachments/{eventId}/`; skip >5 MiB with WARNING |
| Operator | Azure `Calendars.ReadWrite`; `make login` again |

---

## Snapshot / receipt contract

Atomic write: `calendar/snapshot.json.tmp` → replace `calendar/snapshot.json`.

```json
{
  "generated_at": "2026-09-11T16:00:00Z",
  "window": {"start": "2026-08-12T00:00:00Z", "end": "2027-03-10T00:00:00Z"},
  "calendars": [{"id": "cal-work", "displayName": "Work", "isDefault": false}],
  "events": [{
    "id": "evt-standup",
    "calendarId": "cal-work",
    "subject": "Standup",
    "start": {"dateTime": "2026-09-12T13:00:00Z", "timeZone": "UTC"},
    "end": {"dateTime": "2026-09-12T13:30:00Z", "timeZone": "UTC"},
    "isAllDay": false,
    "location": "Room A",
    "bodyPreview": "Daily",
    "categories": ["Work"],
    "attendees": [{"name": "Ada Lovelace", "email": "ada@contoso.com", "type": "required"}],
    "showAs": "busy",
    "sensitivity": "normal",
    "reminderMinutesBeforeStart": 15,
    "lastModifiedDateTime": "2026-09-11T15:00:00Z",
    "attachments": [{"name": "agenda.pdf", "contentType": "application/pdf"}]
  }]
}
```

Receipt (`calendar/receipts/new/{uid-or-localKey}.json`): subject, times, location, categories, calendarId, reminder, showAs, sensitivity, `deleted`, `created`, `localKey`, `modifiedAt`. No `attendees` patch.

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
| `tosser.calendar_snapshot.publish` | entry | Celery publish | calendars= events= |
| `tosser.calendar_snapshot.publish` | exit | snapshot written | path= bytes= |
| `sync.tasks.sync_calendar` | exit | publish+apply | published=1 patched= created= |
| `sync.tasks.sync_calendar` | error | Graph auth fail | reason=auth_failed |
| `taskd.pull` | branch | CAL path missing/unreadable | reachability=down |
| `taskd.apply` | processing | create event | uid= |
| `taskd.apply` | exit | apply done | created= updated= |
| `taskd.apply` | branch | list vs calendar name conflict | project_name_conflict=true |
| `taskd.apply` | branch | attachment over 5 MiB | attachment_skipped=true |
| `taskd.receipts` | exit | receipt queued | uid= or localKey= created= |

Never log tokens, mailbox passwords, event bodies, or attachment bytes.

---

## Tests to Create

| Test | Level | Proves |
|---|---|---|
| `tests/unit/test_calendar_snapshot_parse.py` | unit | Valid event dict; reject missing `id` |
| `tests/unit/test_calendar_project_map.py` | unit | CAL1.2–1.4 shared Projects |
| `tests/unit/test_task_project_map.py` | unit | TASK1.4 extended: calendar join keeps Project |
| `tests/unit/test_calendar_category_apply.py` | unit | CAL1.5 apply only |
| `tests/unit/test_taskd_reachability_down.py` | unit | CAL1.8 missing CAL path |
| `tests/unit/test_calendar_snapshot_log_story_happy.py` | unit caplog | publish entry/exit |
| `tests/unit/test_calendar_log_story_reject.py` | unit caplog | pull branch reachability=down |
| `tests/integration/test_publish_calendar_snapshot.py` | integration | atomic snapshot + attachments |
| `tests/integration/test_calendar_snapshot_create.py` | integration | CAL1.1 inbound event |
| `tests/integration/test_calendar_receipt_patch.py` | integration | CAL1.6 PATCH, no attendees |
| `tests/integration/test_calendar_receipt_create.py` | integration | CAL1.7 POST + ack |
| `tests/integration/test_calendar_attachment_sync.py` | integration | CAL1.9 attachments |
| `tests/integration/test_sync_calendar_log_story_happy.py` | integration caplog | sync_calendar exit |
| `tests/unit/test_celery_app.py` | extend | beat `sync-calendar` schedule 60 |

---

## Implementation Plan

### CAL0 Handoff

- [x] GitHub issue [#10](https://github.com/petelind/o365pop/issues/10) with sections A–G + Lessons Learned inline
- [x] Index issue number in `O365POP_IMPLEMENTATION_PLAN.md`
- [x] Commit `docs(plan): CAL Entourage sync plan Refs #10`
- [x] `gh issue comment` with SHA + slice order

### Slice 1 — CAL1.8 + parse contract

- [ ] Skeleton `deploy/entourage/calendar_snapshot.py` + parse tests
- [ ] Extend `taskd` / `__main__` for `CAL_SNAPSHOT_PATH`
- **Commit**: `feat(taskd): parse calendar snapshot and survive missing path`

### Slice 2 — Graph + publish

- [ ] GraphPort calendar methods + adapters + fixture CAL1.1-standup
- [ ] `tosser/calendar_snapshot.py`, `sync_calendar`, beat, Settings, scope
- **Commit**: `feat(sync): publish Outlook calendar snapshot for Mac taskd`

### Slice 3 — CAL1.2–1.4 Projects (Q15 B)

- [ ] `uid_map.calendars`; amend `_delete_missing_projects`
- **Commit**: `feat(taskd): share Projects by displayName with Outlook calendars`

### Slice 4 — CAL1.5 + CAL1.1 inbound events

- [ ] FakeEntourage events; apply calendar snapshot
- **Commit**: `feat(taskd): apply calendar snapshot events into Entourage`

### Slice 5 — CAL1.6–1.7 receipts

- [ ] Calendar receipts + acks + Graph apply
- **Commit**: `feat(sync): apply Entourage calendar receipts to Graph`

### Slice 6 — CAL1.9 attachments

- [ ] Attachment files publish/apply/receipt
- **Commit**: `feat(sync): sync calendar event attachment files`

### Slice 7 — Deploy + live smoke

- [ ] OsascriptEntourage events; README/plist `CAL_SNAPSHOT_PATH`
- **Commit**: `docs(taskd): calendar snapshot install notes`

**Checkpoint:**
`pytest tests/unit/test_calendar_snapshot_parse.py tests/unit/test_calendar_project_map.py tests/unit/test_task_project_map.py tests/unit/test_calendar_category_apply.py tests/unit/test_taskd_reachability_down.py tests/unit/test_calendar_snapshot_log_story_happy.py tests/unit/test_calendar_log_story_reject.py tests/unit/test_celery_app.py tests/integration/test_publish_calendar_snapshot.py tests/integration/test_calendar_snapshot_create.py tests/integration/test_calendar_receipt_patch.py tests/integration/test_calendar_receipt_create.py tests/integration/test_calendar_attachment_sync.py tests/integration/test_sync_calendar_log_story_happy.py -x`

---

## Definition of Done

- [ ] Checkpoint green (includes log-story tests)
- [ ] `make test` still green
- [ ] No `osascript` in merge-gate tests
- [ ] Azure `Calendars.ReadWrite` documented; human login is operator DoD

---

## Lessons Learned

The TASK hop already proved snapshot + FakeEntourage. The new hazard is **one Project namespace written by two snapshots**: `_delete_missing_projects` will delete calendar-only Projects unless `uid_map.calendars` is checked on every TASK tick. Q19 create needs an ack file because the Mac cannot invent a Graph id. Q20 attachments must stay on disk or the snapshot becomes unreviewable and logs will leak bytes.

---

## Approval

Approved via BPE-01 plan attachment. CAL0 handoff then slices 1–7.

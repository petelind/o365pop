# CAL Q15 C — Implementation Plan

**Feature**: Calendar event → Entourage Project is category name, not calendar displayName
**Feature File**: `docs/features/act-1-bridge/calendar.feature`
**Scenarios**: CAL1.1–CAL1.4 (amended); CAL1.7 target calendar; TASK1.4 list-only delete
**GitHub Issues**: amend [#10](https://github.com/petelind/o365pop/issues/10)
**Branch**: current
**Agent**: Dr. Dobbs v2
**CR**: `docs/plans/CAL_CHANGE_RECONCILIATION.md` (Q15 C)
**Workflow**: BPE-01 plan for the Q15 correction; execute as BPE-09 (test-first bugfix)

Operator lock: Outlook has no Project. Event without category → Entourage Calendar only. Event with category → Calendar **and** Project named after the **first** category (create if missing). Do not mint Project `"Calendar"` from the default mailbox calendar.

---

## Why tests missed it

CAL1.1 fixture used calendar `displayName` `"Work"` **and** category `"Work"`, so calendar→Project and category→Project were indistinguishable. CAL1.2–1.4 asserted the withdrawn Q15 B rule (calendar creates/renames/shares Projects). No test that a default calendar named `"Calendar"` must not create a Project, or that an uncategorized event has an empty project list.

---

## Section A — Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/features/act-1-bridge/calendar.feature` | CAL1.1–1.4, CAL1.7 | Locked Gherkin for Q15 C |
| `deploy/entourage/calendar_apply.py` | `_sync_calendar_projects`, `_event_properties` | Today: calendar id → Project; must become category → Project |
| `deploy/entourage/apply.py` | `_delete_missing_projects` | Drop calendar-join keep-alive |
| `deploy/entourage/calendar_receipts.py` | `_calendar_id_for_project`, `_queue_create_events` | Q19: POST default calendar, not Project-named calendar |
| `tests/unit/test_calendar_project_map.py` | whole file | Replace Q15 B assertions with CAL1.2–1.4 C |

MCP / SAO §17 / §18: **N/A** — no rows.

---

## Section B — Do-Not-Do

- Do NOT create, rename, or delete a Project from Outlook calendar `displayName`
- Do NOT mint Project `"Calendar"` for the default mailbox calendar
- Do NOT mutate the category catalog from calendar apply (CAL1.5)
- Do NOT call Graph from `deploy/entourage/`
- Do NOT mock GraphPort or EntouragePort in integration tests
- Do NOT run `osascript` in `make test`
- Do NOT fold this into mail/POP/SMTP

---

## Section C — SAO.md Sections That Apply

- Design Principles 7 — Mac `taskd` never calls Graph
- §2 Tasks ↔ Entourage — list→Project; TASK1.4 list-only delete
- §2 Calendar ↔ Entourage — first category → Project; calendar is mailbox container only
- §5 Test Strategy — FakeEntourage / FileGraphAdapter
- §11 Observability — apply beats at the category→Project branch

---

## Section D — Tests to Create / Extend

| Test | Level | Asserts |
|------|-------|---------|
| `tests/unit/test_calendar_project_map.py` | unit | CAL1.2: category `"Garden"` creates Project `"Garden"`; no Project `"Calendar"`. CAL1.3: no categories → `project_id` is None; no Project `"Calendar"`. CAL1.4: calendar rename `"Mailbox"` does not create/rename Projects |
| `tests/unit/test_task_project_map.py` | unit | TASK1.4: missing list deletes the joined Project even if `uid_map.calendars` still has a leftover id |
| `tests/integration/test_calendar_snapshot_create.py` | integration | CAL1.1: Project `"Work"` from category; `list_projects()` has no `"Calendar"` |
| `tests/integration/test_calendar_receipt_create.py` | integration | CAL1.7: POST `calendarId` is default `cal-work` even when Project is `"Work"` |
| `tests/unit/test_calendar_category_apply.py` | unit | CAL1.5 still applies catalog names; Project `"Urgent"` may be created (category→Project) without new catalog rows |
| `tests/unit/test_calendar_project_map_log_story_happy.py` | unit caplog | apply branch `project_from_category` / `uncategorized` |

Existing `test_calendar_snapshot_log_story_happy` stays (publish path unchanged).

---

## Section E — Log Story Script

| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `taskd.apply` | branch | event has first category | `project_from_category=true` `name=` (never body) |
| `taskd.apply` | branch | event has no categories | `uncategorized=true` `uid=` |
| `taskd.apply` | branch | calendar displayName would have been a Project under Q15 B | `calendar_is_not_project=true` `name=` |
| `taskd.apply` | exit | snapshot applied | `created=` `updated=` `kind=calendar` |

---

## Section F — MCP Tools to Expose

Not applicable.

---

## Section G — Agent proofs

Not applicable (SAO §17 N/A).

---

## Implementation Steps

1. **Red — CAL1.2–1.4 unit tests** rewrite `test_calendar_project_map.py` to the new Gherkin. Confirm fail (still creates Project from calendar name).
2. **Green — apply** stop `_sync_calendar_projects` from creating/renaming/deleting Projects. Keep `uid_map.calendars` as calendar-id presence for receipts (value may be empty / default marker, not a Project id). `_event_properties` resolves `project_id` from first category via existing Project name or `create_project`.
3. **Green — TASK1.4** `_delete_missing_projects` ignores `uid_map.calendars`. Rewrite `test_deleted_list_keeps_project_when_calendar_join_remains` to prove the list-only delete.
4. **Green — Q19** create receipts use snapshot `isDefault` (or the sole mailbox calendar), not Project displayName. Fixture `CAL1.1-standup` calendar `displayName` becomes `"Calendar"` (`id` stays `cal-work`).
5. **Log story** emit Section E beats in the same commit as behavior.
6. **Regression** `make test` (not `live_graph`).

**Commits** (BPE-09 / Angular):

1. `docs(cal): lock Q15 C category-to-Project mapping`
2. `fix(taskd): join calendar events to Projects by category`

---

## Clarifications locked in this plan

| Topic | Lock |
|-------|------|
| Which category | **First** `categories[]` name is the Project. Extra names apply as Entourage categories only (CAL1.5) |
| Create | Create the Project if missing. Do not create a masterCategory (CAL1.5) |
| Uncategorized | Empty project list; event still created on Entourage Calendar |
| Calendar name | Never a Project, including `"Calendar"` and renames |
| Q19 | POST default mailbox calendar |
| TASK1.4 | Delete Project when the To Do list join is gone |

## Lessons Learned

Q15 B assumed Outlook calendars share names with To Do lists. A live mailbox keeps almost every event on the default calendar named `"Calendar"` and organizes with categories. The CAL1.1 fixture hid that by naming the calendar `"Work"`.

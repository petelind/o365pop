# CAL — Change Reconciliation

**Feature**: Entourage Calendar two-way sync (Outlook appointments/meetings, Projects, Categories)
**Produced by**: BPE-08 Process Change Request
**Date**: 2026-09-11
**Status**: Specs updated in place. Q15 relocked **C — category name** (2026-09-11 operator correction). Prior Q15 B (calendar displayName → Project) is withdrawn.

## Trigger

Operator CR: implement the **same approach** already locked for Tasks & Projects (`TASK_CHANGE_RECONCILIATION.md`) for the Outlook calendar — two-way sync of Appointments/Meetings, and link them to **Projects** and **Categories**.

TASK product path (reused): LibreELEC is the only Graph client; Mac agent never calls Graph; interchange is an atomic JSON snapshot + receipts; injection is Apple Events only; not POP, not `.ics` in Inbox, not an HTTP app.

## Reconciliation matrix

No GUI Screen IDs. Traceability IDs: **CAL1.1–CAL1.9** (Act 6). Mockups N/A (SAO §1 UI: None).

| Layer | Source | Current state (before) | Drift? | Notes |
|---|---|---|---|---|
| User journey | `docs/features/user_journey.md` | Acts 1–5 | Y | Act 6 added |
| Scenarios | `docs/features/act-1-bridge/*.feature` | AUTH–DEP + TASK | Y | `calendar.feature` added; CAL1.2–1.4 are category→Project; TASK1.4 is list-only |
| Mockups | HTML | Absent | N | N/A this stack |
| Screen flow | `docs/ux/dialogue-map.md` | Acts 1–5 | Y | Act 6 subgraph added |
| IA guidelines | `docs/ux/IA_guidelines.md` | CLI + POP/SMTP + Tasks | Y | Calendar surface |
| Prior plan | `docs/plans/O365POP_IMPLEMENTATION_PLAN.md` | Rows 0–7 | Y | Row 8 CAL placeholder |
| Architecture | `docs/architecture/SAO.md` | Mail/Teams + Tasks hop | Y | Calendar hop; `Calendars.ReadWrite` |
| As-built | `o365pop/`, `deploy/entourage/`, tests | No calendar snapshot; no event port | Y | Intentional — BPE-08 does not code |
| Clarifications | `docs/plans/O365POP_Clarifications.md` | Q1–Q14 | Y | Q15–Q20 locked |
| Phrase catalog | `docs/features/CATALOG.md` | AUTH–TASK | Y | CAL rows |
| Fixture catalog | `tests/fixtures/CATALOG.md` | SYNC + TASK | Y | CAL fixtures land with BPE-01 |
| ADE map | `.cursor/rules/_ai-context.mdc` | Mail + taskd | Y | Calendar hop |
| Stack locks | `.cursor/rules/o365pop-stack-locks.mdc` | Tasks not POP | Y | Events not POP |

## Locked target state

```
Graph calendars + calendarView + event attachments + masterCategories (catalog already TASK)
        ↑ GET/POST/PATCH/DELETE
LibreELEC o365pop (Celery)  — writes /storage/o365pop/calendar/snapshot.json
        ↑ pull every 60s (same Mac taskd; no Graph on the Mac)
Mac taskd
        ↔ Apple Events (make new event / project list / category)
Entourage 2008 Calendar events / Projects / Categories
```

- **LibreELEC** remains the only Graph client. New scope: `Calendars.ReadWrite`. Operator re-runs `make login`.
- **Mac `taskd`** (same process as Tasks) never calls Graph, never writes Entourage’s `Database` file, never speaks POP/SMTP.
- **Interchange** is `/storage/o365pop/calendar/snapshot.json` + `calendar/receipts/` + `calendar/attachments/{eventId}/`. Not POP, not `.ics` in Inbox, not an HTTP app.
- **Projects (Q15 C):** Outlook has no Project, only Category. An event with a category joins the Entourage Project named after its **first** category (create if missing). An uncategorized event is Calendar-only. Calendar `displayName` does **not** create, rename, or join a Project. To Do lists still own list→Project (Q10 / TASK1.2–1.4). Amends TASK1.4: drop the calendar-join delete guard.
- **Category catalog** stays TASK-owned. Calendar applies `event.categories[]` only (CAL1.5).
- **Meetings (Q16):** Graph meetings become Entourage `event`. Attendees are text in `content`. Do not set `to recipients`. Do not PATCH Graph `attendees` or send invites from Entourage.
- **Recurrence (Q17):** `GET /me/calendarView` window **−30 / +180 days** (`CAL_WINDOW_PAST_DAYS` / `CAL_WINDOW_FUTURE_DAYS`). One Entourage event per occurrence. Occurrence edit PATCHes that instance. Series-master edit in Entourage is out of v1.
- **Calendars (Q18):** same `taskd`, `CAL_SNAPSHOT_PATH`. All **mailbox** calendars (`GET /me/calendars`). No shared / group / room calendars in v1.
- **Create (Q19):** untagged Entourage events **POST** to Graph. Target is the **default mailbox calendar**. Next snapshot stamps `o365pop-uid:`.
- **Fields (Q20, two-way):** subject, start, end, all-day, location, body/content, categories, project link, reminder, show-as/busy, sensitivity, attachments, event delete. Join key: `o365pop-uid:` in event `content` (Graph event or occurrence id). Last write wins (`modification date` vs `lastModifiedDateTime`).
- **Attachments:** metadata in the snapshot; bytes as files under `calendar/attachments/{eventId}/`. Do not embed base64 in JSON. Do not log file bytes.
- **Deletes:** Graph delete → delete uid-tagged Entourage event. Entourage delete → Graph `DELETE` (unlike POP DELE / Q3).
- **LibreELEC down:** TASK1.8 / Q14 / CAL1.8. WARNING `reachability=down`, retry every 60s.
- **Celery:** `sync_calendar` (`CAL_SNAPSHOT_SECONDS`, default 60). Do not fold into `sync_mailbox` or `sync_tasks`.
- **CI:** `FakeEntourage` + FileGraphAdapter. No `osascript` in `make test`.

## Spec diffs (applied)

| File | Change |
|---|---|
| `docs/plans/CAL_CHANGE_RECONCILIATION.md` | This record |
| `docs/architecture/SAO.md` | Calendar hop, scopes, data, infra |
| `docs/features/user_journey.md` | Act 6 |
| `docs/features/act-1-bridge/calendar.feature` | CAL1.1–1.9 |
| `docs/features/act-1-bridge/tasks.feature` | TASK1.4: delete Project when the list is gone |
| `docs/ux/dialogue-map.md` | Act 6 |
| `docs/ux/IA_guidelines.md` | Calendar surface |
| `docs/plans/O365POP_Clarifications.md` | Q15–Q20; Q10 cross-ref |
| `docs/plans/O365POP_IMPLEMENTATION_PLAN.md` | Row 8 |
| `docs/features/CATALOG.md` | CAL phrases |
| `tests/fixtures/CATALOG.md` | CAL fixtures (land with BPE-01) |
| `.cursor/rules/_ai-context.mdc` | Architecture sketch |
| `.cursor/rules/o365pop-stack-locks.mdc` | Events are not mail |
| `AGENTS.md` | CAL CR pointer |

**Not in this activity:** `CAL_IMPLEMENTATION_PLAN.md`, code, tests, Azure app-registration change (human).

## Locked questions

| # | Question | Locked |
|---|---|---|
| Q15 | Project mapping | **C — category name.** First event category → Project (create if missing). Uncategorized → no Project. Calendar displayName is not a Project. |
| Q16 | Meetings | Entourage `event`. Attendees as text in content. No `to recipients`, no Graph attendee PATCH, no invites. |
| Q17 | Recurrence | `calendarView` −30 / +180 days; one Entourage event per occurrence. |
| Q18 | Agent + which calendars | Same `taskd`; all mailbox calendars; no shared/group/room. (Operator: “yes on all accounts” = both parts of this question.) |
| Q19 | Entourage create → Graph? | **Yes.** Untagged events POST; then stamp `o365pop-uid:`. |
| Q20 | Extra fields | **All included:** reminder, show-as/busy, sensitivity, attachments. |

## Fast path?

No.

## Gate

Operator locked Q15–Q20 on 2026-09-11, then corrected Q15 the same day: category → Project, not calendar displayName. In-place spec revisions for Q15 C are in this record. Implementation plan: `docs/plans/CAL_Q15_FIX_PLAN.md`.

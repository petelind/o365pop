# O365POP Clarifications

Recommended answers are baked into the plan. Change any before implementation starts.

### Q1: One mailbox or many?
**Question**: One Graph account on this LibreELEC box, or many users?
**Recommended**: One `MailboxAccount`. POP/SMTP auth is that one local user.

### Q2: Why not Django?
**Question**: taciturn2 is Django+Celery. Do we need Django here?
**Recommended**: **No.** No web UI, no users, no admin. Keep Celery + Redis + SQLite (`sqlite3`). CLI is `python -m o365pop login`.

### Q3: POP DELE vs Graph?
**Question**: When Entourage deletes, delete in Outlook too?
**Recommended**: Local maildir only. Keep `TossedMessage` so we never re-toss. Graph delete is a later scenario.

### Q4: Which Graph folders?
**Question**: Inbox only, or Inbox+Sent+others?
**Recommended**: Inbox + Teams chats into the **same** POP mailbox (POP has one folder). No folder tree in v1.

### Q5: Redis on LibreELEC?
**Question**: Redis sidecar vs filesystem Celery broker?
**Recommended**: Redis container, same as taciturn2. Filesystem broker is a fallback if Redis is too heavy — not v1.

### Q6: Live Graph in CI?
**Question**: Device-code against the real tenant in the merge gate?
**Recommended**: No. `FileGraphAdapter` / local HTTP fixture for integration. Live Graph is a manual lane-3 smoke on the box.

### Q7: Init git / GitHub issues?
**Question**: This workspace is not a git repo yet.
**Recommended**: After plan approval: `git init`, first docs commit, then one GitHub issue per feature file (AUTH, SYNC, POP, SMTP/SEND, TEAM, DEP).

### Q8: Teams reply mapping?
**Question**: How does Entourage Reply become a Teams chat message?
**Recommended**: Each chat gets `teams.{base32(chat_id)}@o365pop.local` as From/Reply-To plus a minted Message-ID. Scanner routes by In-Reply-To, then by To. Never put the person’s real email on tossed Teams mail. Never sendMail a mapped reply.

### Q9: How do Microsoft tasks reach Entourage?
**Question**: POP flags, `.ics` attachment, Task Request, or Mac AppleScript?
**Recommended**: Mac `taskd` + LibreELEC snapshot files. POP cannot create Tasks. Flag headers are ignored. `.ics` is open-and-save only — not the product path.

### Q10: To Do list ↔ Entourage?
**Question**: Where does a Microsoft To Do list show up?
**Recommended**: Entourage **Project**. Create if missing; rename when the list name changes. Join by Graph list id. Delete the Project when the To Do list is gone (TASK1.4). Outlook calendars do **not** join Projects (Q15).

### Q11: Categories and colors?
**Question**: Which Graph categories, and how do colors map?
**Recommended**: Outlook `masterCategories` ↔ Entourage categories (create / rename / color). `todoTask.categories[]` applied on the Entourage task. Graph `preset0`–`preset24` → nearest Entourage category color (exact table in BPE-01 from the 10.14 dictionary). Delete only categories this sync created.

### Q12: Two-way task fields?
**Question**: Does completing a task in Entourage update To Do?
**Recommended**: Yes for title, due, completed, and task delete, joined by `o365pop-uid:` in task content. Graph owns the list and category catalog. Untagged local tasks stay local. Last write wins.

### Q13: Who talks to Graph?
**Question**: Can the Mac (10.14 + Python 3.13) call Graph itself?
**Recommended**: **No.** Tokens stay on LibreELEC. `taskd` only reads the snapshot and writes receipts.

### Q14: LibreELEC down?
**Question**: What does Mac `taskd` do if the proxy box is off, the share is gone, or the pull times out?
**Recommended**: Stay up. Catch the failure, log one WARNING beat (`reachability=down`), leave Entourage unchanged, keep local receipts queued, sleep until the next 60s tick. Do not raise, do not exit, do not dump a traceback to the operator. Same for a later write of receipts when the box comes back — retry until it works. Calendar snapshot pull uses the same rule (CAL1.8).

### Q15: How does an Outlook event get an Entourage Project?
**Question**: To Do lists already map to Projects (Q10). Outlook has no Project — only Category. How does an event join an Entourage Project?
**Recommended**: **C — category name.** An event with a category joins the Entourage Project of that **first** category name (create the Project if missing). An uncategorized event is Calendar-only (empty project list). Outlook calendar `displayName` does **not** create, rename, or join a Project. The category catalog stays TASK-owned (CAL1.5). To Do lists still map to Projects (Q10 / TASK1.2–1.4).

### Q16: Appointments vs meetings?
**Question**: Sync meetings with attendees two-way (invites / accept / decline)?
**Recommended**: Treat Graph meetings as Entourage `event`. Copy attendees as text in `content`. Do **not** set Entourage `to recipients`. Do **not** PATCH Graph `attendees` or send meeting invites from Entourage.

### Q17: Recurring events?
**Question**: Sync the series master, or each occurrence?
**Recommended**: Expand Graph `calendarView` for **−30 / +180 days** (env: `CAL_WINDOW_PAST_DAYS`, `CAL_WINDOW_FUTURE_DAYS`). One Entourage event per occurrence, joined by occurrence id. Occurrence edit PATCHes that instance. Series-master edit in Entourage is out of v1.

### Q18: Which Mac process, which calendars?
**Question**: New daemon, or same `taskd`? Default calendar only, or all calendars?
**Recommended**: Same `taskd`, second path `CAL_SNAPSHOT_PATH`. All **mailbox** calendars (`GET /me/calendars`). No shared, group, or room calendars in v1.

### Q19: Create events on Graph from Entourage?
**Question**: An Entourage event with no `o365pop-uid:` — POST to Graph, or leave local (like TASK1.7)?
**Recommended**: **Yes, POST.** Target is the **default mailbox calendar** (`isDefault`). Project is category-derived and is not a Graph calendar id. Next snapshot stamps `o365pop-uid:` into content.

### Q20: Which extra event fields?
**Question**: Reminders, show-as/busy, sensitivity, attachments — in or out of v1?
**Recommended**: **All included**, two-way. Attachment bytes live as files under `calendar/attachments/{eventId}/`, not as base64 in `snapshot.json`. Exact Entourage AppleScript tokens are a BPE-01 probe on the 10.14 dictionary.

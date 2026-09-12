# o365pop User Journey

## Personas

**Denis** — Operator
Runs o365pop as a Docker stack on LibreELEC. Has WireGuard inbound. Signs in to Microsoft once via device code over SSH. Reads `logs/app.log` when mail does not appear.

**Vintage Client** — Entourage 2008 (and other POP/SMTP clients)
Lives on a Mac that reaches LibreELEC through WireGuard or LAN. Speaks POP3 on 110 and SMTP on 587 with no SSL. Uses a local mailbox password, not the Microsoft password. Tasks and Calendar come from Mac `taskd` (AppleScript), not from POP.

---

## System Architecture Note

**o365pop**: local Graph-to-POP/SMTP bridge.

- **Celery worker + beat**: Graph pull, inbound toss, outbound scan, task + calendar snapshots (taciturn2 sync shape)
- **popd / smtpd**: wire protocols only; filesystem message base
- **Mac taskd**: snapshot pull + Entourage AppleScript (Tasks / Events / Projects / Categories)
- **Graph REST**: mail MIME + Teams chats + MIME send + To Do + calendars + masterCategories

**Domain model**:

- **MailboxAccount** — one Graph identity + local POP/SMTP credential
- **TossedMessage** — Graph id already dropped into maildir (dedup)
- **SyncSession** — one Celery pull/toss run
- **Maildir** — what POP serves
- **Spool** — what SMTP wrote and the scanner sends
- **Task snapshot** — what `taskd` applies to Entourage Tasks
- **Calendar snapshot** — what `taskd` applies to Entourage Calendar

---

## Critical Architectural Principle

**Daemons do not call Graph. Tosser does not speak POP/SMTP. Mac `taskd` does not call Graph.**

Celery syncs and tosses. POP/SMTP only read/write the message base. That is the taciturn2 split (worker does O365 work; other processes do not) applied to mail.

This separation ensures:

- Entourage dialect bugs stay in popd/smtpd
- Graph throttling/auth stays in sync/tosser
- Tests can prove tosser with fixture Graph and prove POP with a real maildir independently

---

## Journey: Collect and send mail through the bridge

### Act 1: Operator brings the bridge up

**Context**: LibreELEC has Docker and WireGuard. No Microsoft token yet.

Denis SSHs in, starts the compose stack, runs `make login`, completes device-code in a browser on another machine. Tokens land encrypted on `/storage`. Beat starts pulling.

### Act 2: Vintage client collects inbound

**Context**: Graph has a new Inbox message and a new Teams chat line.

Beat runs `sync_mailbox`. Tosser drops RFC822 into maildir (Outlook via `$value` MIME; Teams synthesized). Entourage POP USER/PASS, UIDL, RETR. Message appears in the client. If Entourage DELE, the file leaves maildir; Graph keeps the original; next sync does not re-toss.

### Act 3: Vintage client sends outbound

**Context**: Denis composes in Entourage and sends.

smtpd accepts AUTH LOGIN + DATA, writes spool. Beat/worker scans spool:

- Ordinary mail → Graph `sendMail` (raw MIME)
- Reply to a tossed Teams message (`In-Reply-To` or `To: teams.{chat}@o365pop.local`) → Graph chat post, not email

Success → `spool/sent/`. Failure → retry then `spool/failed/` and a log error.

### Act 4: Reply to a Teams chat as email

**Context**: Denis collected a synthesized Teams message (`From: "Ada Lovelace" <teams.xxx@o365pop.local>`). He hits Reply in Entourage.

Entourage sends SMTP to that address (and usually sets `In-Reply-To` to our `Message-ID`). The scanner maps address / Message-ID → `ChatMap` / `TossedMessage` and posts the reply text into the same chat. Ada sees it in Teams. Nothing is sent as Outlook mail.

### Act 5: Vintage client works Tasks in Entourage

**Context**: Graph has To Do lists and Outlook categories. POP cannot create Entourage Tasks.

LibreELEC publishes `/storage/o365pop/tasks/snapshot.json`. Every minute `taskd` on the Entourage Mac pulls it and AppleScripts Tasks, Projects (one per To Do list), and categories (colors mapped from Outlook). Completing or editing a uid-tagged task writes a receipt; Celery PATCHes Graph. Untagged local tasks stay local. If LibreELEC is down, `taskd` stays running, logs a WARNING, and retries the next minute — it does not crash.

### Act 6: Vintage client works Calendar in Entourage

**Context**: Graph has Outlook calendars and events. POP cannot create Entourage events.

LibreELEC publishes `/storage/o365pop/calendar/snapshot.json` (window −30 / +180 days) and attachment files. The same `taskd` AppleScripts Entourage `event` objects: Project from the event’s first category name (create if missing; uncategorized stays Calendar-only — Q15), categories from the TASK catalog, attendees as text in content (not meeting invites). Editing a uid-tagged event PATCHes Graph. A new Entourage event with no uid POSTs to the default mailbox calendar, then the next snapshot stamps `o365pop-uid:`. Reminders, show-as, sensitivity, and file attachments sync both ways. Recurring series expand to one Entourage event per occurrence. If LibreELEC is down, the same quiet retry as Act 5.

---

## Acts and feature files

| Act | Feature file | Plan |
|---|---|---|
| Scaffold | — | `docs/plans/BOOT_IMPLEMENTATION_PLAN.md` |
| Auth + token refresh | `docs/features/act-1-bridge/auth.feature` | `docs/plans/AUTH_IMPLEMENTATION_PLAN.md` |
| Inbound sync + toss | `docs/features/act-1-bridge/inbound.feature` | `docs/plans/SYNC_IMPLEMENTATION_PLAN.md` |
| POP collect | `docs/features/act-1-bridge/pop.feature` | `docs/plans/POP_IMPLEMENTATION_PLAN.md` |
| SMTP + send | `docs/features/act-1-bridge/smtp.feature` | `docs/plans/SMTP_IMPLEMENTATION_PLAN.md` |
| Teams reply map | `docs/features/act-1-bridge/teams.feature` | `docs/plans/TEAM_IMPLEMENTATION_PLAN.md` |
| LibreELEC deploy | `docs/features/act-1-bridge/deploy.feature` | `docs/plans/DEP_IMPLEMENTATION_PLAN.md` |
| Entourage Tasks | `docs/features/act-1-bridge/tasks.feature` | `docs/plans/TASK_IMPLEMENTATION_PLAN.md` |
| Entourage Calendar | `docs/features/act-1-bridge/calendar.feature` | BPE-08 `docs/plans/CAL_CHANGE_RECONCILIATION.md` (BPE-01 later) |

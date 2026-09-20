# o365pop: System Architecture Overview

## Executive Summary

o365pop is a local LibreELEC daemon that lets vintage mail clients (Entourage 2008 and peers) talk to Microsoft 365. WireGuard is the security layer. POP3 and SMTP stay 1998-compatible (no TLS, USER/PASS, AUTH LOGIN). Celery owns Graph sync and Fido-style tossing. Separate POP and SMTP daemons own the wire protocols only. A second process on the Entourage Mac (`taskd`) syncs Microsoft To Do, Outlook calendar, and Outlook categories into Entourage Tasks / Calendar / Projects / Categories via Apple Events — not via POP.

Key decisions:

- Plain Python package + SQLite + Celery + Redis — taciturn2’s **process** model (worker/beat), not Django.
- One mailbox (one Graph account) per deployment.
- Honest Graph REST over `httpx` — no Microsoft SDK, no taciturn2/microsoft-mcp reuse.
- Inbound: Graph → tosser → maildir. Outbound: Entourage SMTP → spool → scanner → Graph `sendMail` (raw MIME) **or** Teams chat post when the reply maps to a tossed chat.
- Tasks: Graph To Do + masterCategories → snapshot files on LibreELEC → Mac `taskd` (Python + `osascript`) → Entourage Tasks / Projects / Categories. Two-way on task title, due, completed, and task delete.
- Calendar: Graph calendars + `calendarView` → `/storage/o365pop/calendar/` snapshot → same Mac `taskd` → Entourage events. Two-way on subject, times, location, body, categories, project, reminder, show-as, sensitivity, attachments, create, and delete (CAL Q15–Q20).
- POP/SMTP bind to the WireGuard address (optional LAN). Never the WAN NIC.
- Device-code MSAL login; Fernet-encrypted tokens; local POP/SMTP password is not the Microsoft password.

## Design Principles

1. **Daemons never call Graph.** `popd` / `smtpd` only speak wire protocols against the filesystem message base.
2. **Tosser never speaks POP/SMTP.** Celery owns pull, toss, scan, and reply routing.
3. **One mailbox per deployment.** Single Graph account; single local POP/SMTP credential.
4. **WireGuard is the crypto.** POP/SMTP stay 1998-cleartext on the tunnel bind, never the WAN NIC.
5. **Honest Graph REST.** `httpx` + MSAL only — no Graph SDK, no taciturn2 client reuse.
6. **Prove with real bytes.** Integration tests use real maildir, real daemons, and FileGraphAdapter fixtures — no service mocks.
7. **Mac `taskd` never calls Graph.** LibreELEC never AppleScripts Entourage. Tasks and Calendar events do not go through POP. Do not write Entourage’s `Database` file.

## 1. Application Blocks

### Bounded contexts

| Package | Responsibility |
|---|---|
| `accounts` | Mailbox account, encrypted Graph tokens, local POP/SMTP credential |
| `graph` | Thin Graph REST client (`httpx`). Mail list, MIME `$value`, chats, MIME send, chat post, To Do lists/tasks, masterCategories, calendars, calendarView, event attachments |
| `tosser` | Inbound convert+drop into maildir; outbound scan spool; **reply router** (mail vs Teams); **task + calendar snapshot** writers |
| `mailstore` | Maildir + SMTP spool + tossed-index (dedup) + task and calendar snapshot/receipts dirs |
| `popd` | POP3 protocol only — reads maildir |
| `smtpd` | SMTP protocol only — writes spool |
| `sync` | Celery tasks + beat: pull Graph, toss inbound, scan outbound, publish task and calendar snapshots, apply receipts |
| `taskd` (Mac) | Launchd agent: pull task + calendar snapshots every 60s; AppleScript Entourage Tasks/Events/Projects/Categories; write receipts |

### Module dependency rules

```
popd, smtpd     -->  mailstore
sync tasks      -->  tosser --> graph, mailstore, accounts
graph           -->  accounts (token only)
taskd (Mac)     -->  snapshot files, osascript  (never graph)
```

Daemons must not import `graph`. Tosser must not speak POP/SMTP. Mac `taskd` must not import `o365pop.graph` and must not hold Azure tokens.

### Foundational pattern

**Chosen:** Fido tosser + Celery job worker (taciturn2 sync shape).

**Rationale:** taciturn2 already proves periodic O365 sync behind Celery beat/worker with session status, timeouts, and no retry loops on auth failure. o365pop reuses that job shape. Mail clients stay on dumb protocol daemons in front of a filesystem message base.

### UI

None. Operator surface is `python -m o365pop login` plus `logs/app.log`. No web framework, no HTMX, no Playwright.

## 2. Integration & API Design

### External: Microsoft Graph REST

- Base: `https://graph.microsoft.com/v1.0`
- Auth: MSAL public client, device-code flow, scopes `Mail.Read`, `Mail.Send`, `Chat.ReadWrite`, `User.Read`, `Tasks.ReadWrite`, `MailboxSettings.Read`, `Calendars.ReadWrite`, `offline_access`
- Inbound mail: list Inbox (`/me/mailFolders/inbox/messages`) then `GET /me/messages/{id}/$value` for raw RFC822
- Inbound chats: `/me/chats` + `/me/chats/{id}/messages` — tosser synthesizes RFC822 **with a stable reply map** (below)
- To Do: `GET /me/todo/lists`, `GET /me/todo/lists/{id}/tasks`; `PATCH`/`DELETE` a task from Mac receipts
- Outlook categories: `GET /me/outlook/masterCategories` (`color` is `preset0`–`preset24` or `none`)
- Calendar: `GET /me/calendars`; `GET /me/calendarView` (window −30 / +180 days) with `Prefer: outlook.body-content-type="text"`; if Graph still returns HTML, LibreELEC BeautifulSoup publishes already-plain `body` + `bodyContentType=text` (Mac `taskd` stays stdlib-only); `POST`/`PATCH`/`DELETE` `/me/events/{id}`; event attachments as files, not JSON base64
- Outbound mail: `POST /me/sendMail` with `Content-Type: text/plain` and **base64-encoded** RFC822 (Graph rejects raw MIME: `ErrorMimeContentInvalidBase64String`)
- Outbound Teams reply: `POST /chats/{chat-id}/messages` — never `sendMail`
- Client: our `graph` package only. No Graph SDK. Mac `taskd` does not call Graph.

### Teams ↔ email reply map

Each Teams chat gets one stable email identity. Entourage Reply must come back as a chat post, not an Outlook message to the person’s real address.

**Inbound mint** (tosser, every tossed Teams RFC822):

| Header | Value |
|---|---|
| `Message-ID` | `<teams.{chat_b32}.{msg_b32}@o365pop.local>` |
| `From` | `"Ada Lovelace" <teams.{chat_b32}@o365pop.local>` |
| `Reply-To` | same address as `From` |
| `X-O365POP-Source` | `teams` |
| `X-O365POP-Chat-Id` | raw Graph chat id |
| `X-O365POP-Message-Id` | raw Graph message id |

`chat_b32` / `msg_b32` = lowercase base32 of the UTF-8 Graph id, no padding. Chat ids like `19:abc@thread.v2` are not legal email local-parts.

Graph Teams bodies are usually HTML. Toss as `multipart/alternative` (`text/plain` + `text/html`) so Entourage 2008 renders the message instead of showing raw tags. Do not convert to RTF.

**Do not** put the person’s real SMTP address in `From` or `Reply-To`. Entourage 2008 replies to `From`/`Reply-To` and sometimes drops custom `X-` headers; the special address is the durable map.

**Outbound route** (`OutboundRouter`, scanner — not smtpd):

1. `In-Reply-To` or `References` matches a `TossedMessage.message_id` with `source=teams` → chat post
2. Else any `To`/`Cc` is `teams.{chat_b32}@o365pop.local` → decode → chat post
3. Else `sendMail`
4. Any `@o365pop.local` that does not decode → `spool/failed/`, **never** `sendMail`

Chat post body = text before the first quoted block (`>`, `From:`, `-----Original Message-----`). Log if we fall back to the full body.

`ChatMap` row: `chat_id` ↔ `chat_b32` ↔ `reply_address` (one row per chat, reused for every message in that chat).

### Tasks ↔ Entourage (not POP)

POP cannot create Entourage Tasks. `X-Message-Flag` is ignored on RETR. A `VTODO` `.ics` attachment works only after open-and-save. The product path is a **snapshot + Mac AppleScript** hop (BPE-08 `TASK_CHANGE_RECONCILIATION.md`).

**LibreELEC (Celery):** pull To Do lists/tasks and masterCategories; write an atomic `/storage/o365pop/tasks/snapshot.json`; apply Mac receipt files (`PATCH`/`DELETE` Graph).

**Mac `taskd` (launchd, every 60s):** copy/read that snapshot (LAN or WireGuard file access); AppleScript Entourage; write receipts. Python 3.13 stdlib + `osascript`. No pip Graph stack on the Mac. If the LibreELEC host is unreachable, `taskd` keeps running and retries each tick — it does not crash or surface an exception (TASK1.8).

| Graph | Entourage | Sync |
|---|---|---|
| To Do list (`/me/todo/lists`) | Project | Create if missing; rename when `displayName` changes; delete Project when the list is gone (TASK1.4). Calendars do not join Projects (Q15). |
| todoTask | Task | Create/update title, due, completed; `content` holds `o365pop-uid: {task-id}`; list → Project; `categories[]` → Entourage categories |
| masterCategory | Category | Create if missing; rename with `displayName`; set color from Graph `color` via palette map; delete only sync-created categories |

Two-way task fields: title, due, completed, task delete. Last write wins (`modification date` vs `lastModifiedDateTime`). Tasks without `o365pop-uid:` stay local. Graph owns the list and category **catalog**.

Do **not** mint Tasks as RFC822. Do **not** write `~/Documents/Microsoft User Data/**/Database`.

### Calendar ↔ Entourage (not POP)

Meeting Request mail and `.ics` attachments are not the Calendar product. The path is a **snapshot + Mac AppleScript** hop (BPE-08 `CAL_CHANGE_RECONCILIATION.md`).

**LibreELEC (Celery):** pull mailbox calendars and `calendarView` (−30 / +180 days); write atomic `/storage/o365pop/calendar/snapshot.json` plus `calendar/attachments/{eventId}/`; apply Mac receipts (`POST`/`PATCH`/`DELETE` Graph events and attachments).

**Mac `taskd` (same launchd agent as Tasks, every 60s):** read `CAL_SNAPSHOT_PATH`; AppleScript Entourage `event` (`project list`, `category`); write receipts. Unreachable LibreELEC is CAL1.8 (same quiet retry as TASK1.8).

| Graph | Entourage | Sync |
|---|---|---|
| Calendar (`/me/calendars`) | mailbox container only | Sync events from all mailbox calendars (Q18). `displayName` does **not** create or rename an Entourage Project |
| event / calendarView occurrence | event | Create/update subject, start, end, all-day, location, body; `content` holds `o365pop-uid:`; first `categories[]` name → Project (create if missing); uncategorized → empty project list; `categories[]` → category list (catalog is TASK); reminder; show-as; sensitivity; file attachments |
| event attendees | text in `content` | Display only. Do not set `to recipients`. Do not PATCH Graph attendees |
| event attachments | event file attachments | Bytes on disk under `calendar/attachments/{eventId}/` |

Two-way event fields: Q20 set plus create (Q19) and delete. Last write wins. Untagged Entourage events **POST** to the default mailbox calendar; next snapshot stamps the uid. Graph owns the category **catalog** (TASK). No shared/group/room calendars in v1.

Do **not** mint Calendar as RFC822. Do **not** write Entourage’s `Database` file.

### Client-facing: POP3 + SMTP

- POP3 `:110` — **Twisted** `twisted.mail.pop3` over maildir. USER/PASS, STAT, LIST, RETR, DELE, UIDL, TOP, CAPA, QUIT. No APOP, no STLS. `popd` is its own process (Twisted reactor). Do not run it inside the aiosmtpd event loop.
- **Palm view (same `popd`, same `:110`):** USER `palm` + the local mailbox password. Same maildir, different IMailbox: UIDL is a SHA-256 hex hash (64 chars, never the Graph id); last 24h only; RETR is text/plain `7bit` CRLF with Date set and headers folded; size ≤5 KB after rewrite; no multipart / Teams HTML. USER `MAILBOX_USER` (Entourage) is unchanged. Palm DELE hides the hash for that view only — it does not delete the maildir file.
- SMTP `:587` (optional `:25`) — EHLO, AUTH LOGIN, AUTH PLAIN, MAIL/RCPT/DATA. No STARTTLS, no XOAUTH2.
- Contract tests use a real `poplib` / `smtplib` client against the daemons.

### Inter-process

- Redis broker + result backend (taciturn2 default).
- Filesystem message base: maildir (inbound), spool (outbound), `tasks/snapshot.json` + `tasks/receipts/` (Entourage Tasks), `calendar/snapshot.json` + `calendar/receipts/` + `calendar/attachments/` (Entourage Calendar).
- SQLite for account, sync sessions, tossed-index, task-list/category join (LibreELEC). Mac keeps a local uid map next to `taskd`.

## 3. Code Organization

```
o365pop/                 # installable package (config, celery_app, cli, db)
  accounts/              # MailboxAccount, token helpers, device-code login
  graph/                  # GraphPort + HttpGraphAdapter
  tosser/                 # inbound_tosser, outbound_scanner, mime_factory, router, task_snapshot, calendar_snapshot
  mailstore/              # MaildirStore, SpoolStore
  popd/                   # Twisted POP3 daemon (IMailboxPOP3 → maildir)
  smtpd/                  # aiosmtpd handler
  sync/                   # Celery tasks (pull, toss, scan, cleanup, task + calendar snapshot)
tests/{unit,integration,fixtures,support}
deploy/{Dockerfile,docker-compose.yml,libreelec/,entourage/}   # entourage = Mac taskd
logs/app.log
docs/{architecture,features,plans}
```

Reuse **patterns** from taciturn2 (see Context Map in the plan). Do not vendor taciturn2 source.

## 4. Data Architecture

| Store | What |
|---|---|
| SQLite | `MailboxAccount`, `SyncSession`, `TossedMessage` (graph_id, source, message_id, chat_id, uidl), `ChatMap`, To Do list/category join rows |
| Maildir | RFC822 messages Entourage collects |
| Spool `new/` `retry/` `sent/` `failed/` | Outbound RFC822 from SMTP |
| `tasks/snapshot.json` + `tasks/receipts/` | Task catalog for Mac `taskd`; Entourage→Graph receipts |
| `calendar/snapshot.json` + `calendar/receipts/` + `calendar/attachments/` | Calendar catalog for Mac `taskd`; Entourage→Graph receipts; attachment bytes |
| Redis | Celery only — not a message store |
| Encrypted fields | Graph access + refresh tokens (Fernet, `TOKEN_ENCRYPTION_KEY`) |

Single `MailboxAccount` row in v1. POP UIDL = stable hash of Graph id (or generated id for synthesized Teams mail). `DELE` removes from maildir only; `TossedMessage` prevents re-toss and stores the RFC822 `Message-ID` used for reply routing. **Task** delete is not POP DELE: a uid-tagged Entourage delete is a Graph task `DELETE` (Q12). **Calendar** delete is the same shape for uid-tagged events (Q19/Q20).

## 5. Test Strategy

Pointer: [`docs/architecture/test-architecture.md`](test-architecture.md). Catalogs: [`docs/features/CATALOG.md`](../features/CATALOG.md), [`tests/fixtures/CATALOG.md`](../../tests/fixtures/CATALOG.md).

TFK-01 re-run 2026-09-05 against Edda v73. Stock Trophy (behave-django + Playwright) does **not** apply: there is no web UI (SAO §1). Gherkin in `docs/features/` is the requirements document; pytest integration tests are the executable engine. SAO §17 (agent lanes) is **N/A** — no ScriptedLLM, no `llm_scripts/`, no `make test-agent-proof`.

| Stock v73 | o365pop |
|---|---|
| behave-django AT (`make test-at`) | Skip — phrases catalogued, proven by pytest |
| Playwright E2E (`make test-e2e`) | Skip Playwright — `tests/live/` + `@live_graph` is the operator journey |
| Agent lanes 1–4 | Skip — SAO §17 N/A |
| FactoryBoy / AutoFixture | Skip — FileGraphAdapter + JSON presets |

### Test Trophy (daemon-adjusted)

| Level | Weight | Runner | What it proves |
|---|---|---|---|
| Unit | Thin | `pytest -m unit` | Pure logic: chat address codec, MIME factory, reply router, task/calendar snapshot/receipt parse, Fernet vault, AUTH LOGIN decoder, POP command parse. Do **not** test sqlite3/`mailbox` framework behavior. Mac `osascript` is proven live on the Entourage host, not in CI. |
| Integration | **Thick** | `pytest -m integration` | Feature works with real maildir, real aiosmtpd, real Twisted POP daemon, real sqlite, Celery `task_always_eager`. Graph via `FileGraphAdapter` (disk JSON/MIME) or a local HTTP fixture server. **No `unittest.mock` on services.** |
| Acceptance | Spec | Gherkin in `docs/features/act-*/` | Executable requirements. Each scenario maps to a pytest module in the Step Library Catalog. No behave runner. |
| E2E / live | Selective | `@pytest.mark.live_graph` | Device-code against Denis’s tenant. **Not** a PR merge gate. No Playwright. |

### Why Trophy over Pyramid

- Unit tests of `sqlite3.connect` or `Maildir.add` prove nothing about toss/dedup/DELE.
- A browser E2E suite does not exist — Entourage is the client; we speak POP/SMTP in-process.
- Integration (real daemons + fixture Graph) is the sweet spot: real bytes, no GUI, fast enough for `make test`.

### Runner mapping

| Command | What |
|---|---|
| `make test` | `pytest tests/ -m "not live_graph"` — merge gate |
| `make test-unit` | `pytest tests/unit/ -m unit` |
| `make test-integration` | `pytest tests/integration/ -m integration` |
| `make test-log-story` | `pytest -m log_story` — caplog beats via `assert_log_story` |
| `make test-live-graph` | `pytest -m live_graph` — operator-only |
| `make test-e2e` | `pytest tests/live/ -m live_graph -s` — captured-login journey (Acts 1–4; Act 5–6 on the Entourage Mac) |

Default collection **excludes** `live_graph`. `make test-at` / `make test-agent-*` are documented no-ops (TFK-05). `make test-e2e` is the live journey, not Playwright.

### Coverage policy

Coverage numbers are necessary but not sufficient. Quality gates:

- No mocks in integration tests (`do-not-mock-in-integration-tests`)
- Log-story tests ship in the **same commit** as the behavior they prove (`do-assert-log-story`)
- Never assert raw tokens, mailbox passwords, or raw MIME bodies
- Checkpoint = one pytest command per feature plan (see `docs/plans/`)

### Zero-bug and zero-length feedback

A bug is a failing unit/integration scenario. Fix the same day and add a permanent regression test (`do-update-tests-after-bugfixing`). Continuous pytest writes `tests.log`. `make test-watch` re-runs on `.py` changes.

### Layout

```
tests/
  unit/                 # pytest -m unit
  integration/          # pytest -m integration (no mocks)
  live/                 # @live_graph operator journey (captured login)
  fixtures/             # Graph cases, RFC822, presets — see tests/fixtures/CATALOG.md
  support/
    log_story.py        # assert_log_story(caplog, where=..., beats=...)
    fixtures.py         # load_graph_case / load_mail / load_preset
    mailbox.py          # isolated maildir / spool / sqlite
docs/features/
  act-1-bridge/*.feature
  CATALOG.md            # phrase → pytest helper (TFK-03; no behave steps)
```

### Graph in tests

| Mode | When | How |
|---|---|---|
| FileGraphAdapter | PR / `make test` | `tests/fixtures/graph/<case>/` |
| Live Graph | `@live_graph` only | Device-code; never merge-gate |

### Log story

Helper: `from tests.support.log_story import assert_log_story`.

```python
assert_log_story(
    caplog,
    where="HealthCheck.run",
    beats={"entry": ["probe=bootstrap"], "exit": ["status=ok"]},
)
```

Format in `logs/app.log`: `{logger} | {Class.method} | {beat} | key=value`. Beats: `entry → config → validation → processing → branch → exit → error`.

### Agent lanes

**Skip.** No SAO §17. Do not add `agent_proof` / `live_llm` / `quality` markers or empty `llm_scripts/` trees.

## 6. Performance & Scalability

- One user, one worker (`prefetch=1`), beat every 2 minutes inbound / 30 seconds outbound / **60 seconds** task snapshot / **60 seconds** calendar snapshot
- Graph page size ≤ 50; respect `Retry-After`
- Soft time limit 10 minutes per sync (LibreELEC, not taciturn2’s 55-minute task dumps)
- Mac `taskd` interval: 60 seconds (operator CR)

## 7. Error Handling & Resilience

Copy taciturn2 `sync_user_o365_data` shape:

- Auth failure: mark session failed, **do not retry** (avoids lockout loops)
- Graph 429: pause session, retry after `Retry-After` (or 120s)
- SoftTimeLimit: mark failed, return error dict
- Outbound send fail: leave message in `spool/retry/`; after N attempts move to `spool/failed/`
- Never delete Graph mail because POP `DELE` happened
- Task and calendar receipt apply: same auth-fail / 429 shape as mail sync; do not retry-lock the mailbox
- **Mac `taskd` if LibreELEC is down** (timeout, connection refused, share missing): catch, log WARNING `reachability=down`, do not raise, do not exit, do not print a traceback. Leave Entourage unchanged. Queue receipts locally. Retry on the next 60s tick until the box is back (Q14 / TASK1.8 / CAL1.8)

## 8. Infrastructure

- Runtime: Docker on LibreELEC (`service.system.docker`), `--network host`
- Compose services: `redis`, `worker`, `beat`, `popd`, `smtpd`
- Persist `/storage/o365pop/{data,maildir,spool,logs,tasks,calendar}`
- Listen: `POP3_BIND` / `SMTP_BIND` (WireGuard IP). Default not `0.0.0.0` unless `ALLOW_LAN=1`
- Mac: `deploy/entourage/` + launchd (`taskd` every 60s). Entourage host is macOS 10.14.6 + Office 2008 (pilot: `Deniss-MacBook-Pro-2.local`)

## 9. CI/CD Pipeline

v1 merge gate is local (and optional GitHub Actions): `make provision && make lint && make test`. That is TFK-05. No cloud deploy. `@live_graph` is never a PR job. DCD may add a richer pipeline later.

## 10. Release & Rollback

Docker image tag on the LibreELEC host. Rollback = previous image + unchanged volumes. Maildir/SQLite are the recovery point.

## 11. Observability

- `logs/app.log` — RotatingFileHandler, truncate/rotate on process start
- Format: `{logger} | {Class.method} | {beat} | key=value`
- Beats: `entry → config → validation → processing → branch → exit → error`
- Never log tokens, mailbox password, or raw MIME bodies (log sizes, ids, subjects only)
- Celery task id + sync session id on every sync/toss line

## 12. Config & Secrets

Environment / `.env` on `/storage` (not in the image):

- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` (`common` allowed)
- `TOKEN_ENCRYPTION_KEY`
- `MAILBOX_USER`, `MAILBOX_PASSWORD` (local POP/SMTP)
- `POP3_BIND`, `POP3_PORT`, `SMTP_BIND`, `SMTP_PORT`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `GRAPH_POLL_SECONDS`, `SPOOL_SCAN_SECONDS`, `TASK_SNAPSHOT_SECONDS`, `CAL_SNAPSHOT_SECONDS` (LibreELEC publish; default 60)
- `CAL_WINDOW_PAST_DAYS` (default 30), `CAL_WINDOW_FUTURE_DAYS` (default 180)
- Mac `taskd`: `TASK_SNAPSHOT_PATH` / `CAL_SNAPSHOT_PATH` (or URL) to each `snapshot.json`; `TASK_POLL_SECONDS` (default 60)

## 13. Security

- WireGuard encrypts the client hop. POP/SMTP are intentionally cleartext **inside** the tunnel.
- Do not bind 110/587 on the public NIC.
- Local mailbox password ≠ Microsoft password.
- Tokens encrypted at rest. Device-code login over SSH, not a browser on LibreELEC.
- Entourage must not be given the Azure password.
- Mac `taskd` holds no Graph tokens. Snapshot and receipts are not secrets; still do not log task/event bodies or attachment bytes.

## 14. Backup & Recovery

Back up `/storage/o365pop/data` (SQLite + tokens), maildir, `tasks/`, and `calendar/`. Spool `failed/` is operator-visible. Token loss ⇒ device-code login again. Rebuild of Entourage Tasks and Calendar from a fresh snapshot is the Mac recovery path (uid map can be reconstructed from `o365pop-uid:` in task/event content).

## 15. Developer Experience

- `make provision` `make test` `make test-unit` `make test-integration` `make test-log-story` `make test-watch`
- `make worker` `make beat` `make popd` `make smtpd` `make login`
- Mac: `deploy/entourage/taskd.py` under launchd (not in Docker)
- pytest + Celery `task_always_eager` in unit/integration
- Dr. Dobbs v2: skeleton → red → green → refactor; methods ≤ 30 lines

## 16. Documentation Strategy

- This SAO is the architecture lock
- Process: `docs/process/MODUS_OPERANDI.md`; ADE: `.cursor/rules/_ai-context.mdc` (Cursor)
- Feature files in `docs/features/act-*/`; phrase map in `docs/features/CATALOG.md`
- Fixture catalog in `tests/fixtures/CATALOG.md`
- Plan in `docs/plans/O365POP_IMPLEMENTATION_PLAN.md`; TASK CR in `docs/plans/TASK_CHANGE_RECONCILIATION.md`; CAL CR in `docs/plans/CAL_CHANGE_RECONCILIATION.md`
- Update `_ai-context.mdc` when SAO sections change

## Technology Stack Table

| Layer | Choice |
|---|---|
| Language | Python 3.12+ (LibreELEC); Python 3.13 stdlib on the Entourage Mac (pilot 10.14.6) |
| App | Plain Python package + `python -m o365pop` CLI |
| Jobs | Celery + Redis (taciturn2 pattern) |
| Graph | `httpx` + `msal` |
| SMTP server | `aiosmtpd` |
| POP server | **Twisted** `twisted.mail.pop3` + `MaildirMailbox` |
| Tasks / Calendar client | Mac `taskd` + `osascript` → Microsoft Entourage |
| Message base | stdlib `mailbox.Maildir` + `tasks/snapshot.json` + `calendar/snapshot.json` |
| DB | SQLite |
| Deploy | Docker Compose on LibreELEC; launchd on the Entourage Mac |

## SAO sections that govern implementation

- §1 Application Blocks — daemon vs tosser vs Mac `taskd`
- §2 Integration — Graph REST + POP/SMTP dialect + Tasks and Calendar snapshot hops
- §3 Code Organization
- §4 Data Architecture — tossed-index, local DELE, task + calendar snapshots
- §5 Test Strategy — no mocks in integration; osascript not in CI
- §7 Error Handling — taciturn2 sync failure shape
- §8 Infrastructure — LibreELEC / WireGuard binds / Mac launchd
- §11 Observability — log story
- §13 Security — WG is the crypto; no Azure password on POP or on `taskd`

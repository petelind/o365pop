# o365pop: System Architecture Overview

## Executive Summary

o365pop is a local LibreELEC daemon that lets vintage mail clients (Entourage 2008 and peers) talk to Microsoft 365. WireGuard is the security layer. POP3 and SMTP stay 1998-compatible (no TLS, USER/PASS, AUTH LOGIN). Celery owns Graph sync and Fido-style tossing. Separate POP and SMTP daemons own the wire protocols only.

Key decisions:

- Plain Python package + SQLite + Celery + Redis — taciturn2’s **process** model (worker/beat), not Django.
- One mailbox (one Graph account) per deployment.
- Honest Graph REST over `httpx` — no Microsoft SDK, no taciturn2/microsoft-mcp reuse.
- Inbound: Graph → tosser → maildir. Outbound: Entourage SMTP → spool → scanner → Graph `sendMail` (raw MIME) **or** Teams chat post when the reply maps to a tossed chat.
- POP/SMTP bind to the WireGuard address (optional LAN). Never the WAN NIC.
- Device-code MSAL login; Fernet-encrypted tokens; local POP/SMTP password is not the Microsoft password.

## 1. Application Blocks

### Bounded contexts

| Package | Responsibility |
|---|---|
| `accounts` | Mailbox account, encrypted Graph tokens, local POP/SMTP credential |
| `graph` | Thin Graph REST client (`httpx`). Mail list, MIME `$value`, chats, MIME send, chat post |
| `tosser` | Inbound convert+drop into maildir; outbound scan spool; **reply router** (mail vs Teams) |
| `mailstore` | Maildir + SMTP spool + tossed-index (dedup) |
| `popd` | POP3 protocol only — reads maildir |
| `smtpd` | SMTP protocol only — writes spool |
| `sync` | Celery tasks + beat: pull Graph, toss inbound, scan outbound |

### Module dependency rules

```
popd, smtpd  -->  mailstore
sync tasks   -->  tosser --> graph, mailstore, accounts
graph        -->  accounts (token only)
```

Daemons must not import `graph`. Tosser must not speak POP/SMTP.

### Foundational pattern

**Chosen:** Fido tosser + Celery job worker (taciturn2 sync shape).

**Rationale:** taciturn2 already proves periodic O365 sync behind Celery beat/worker with session status, timeouts, and no retry loops on auth failure. o365pop reuses that job shape. Mail clients stay on dumb protocol daemons in front of a filesystem message base.

### UI

None. Operator surface is `python -m o365pop login` plus `logs/app.log`. No web framework, no HTMX, no Playwright.

## 2. Integration & API Design

### External: Microsoft Graph REST

- Base: `https://graph.microsoft.com/v1.0`
- Auth: MSAL public client, device-code flow, scopes `Mail.Read`, `Mail.Send`, `Chat.ReadWrite`, `User.Read`, `offline_access`
- Inbound mail: list Inbox (`/me/mailFolders/inbox/messages`) then `GET /me/messages/{id}/$value` for raw RFC822
- Inbound chats: `/me/chats` + `/me/chats/{id}/messages` — tosser synthesizes RFC822 **with a stable reply map** (below)
- Outbound mail: `POST /me/sendMail` with `Content-Type: text/plain` and raw MIME body
- Outbound Teams reply: `POST /chats/{chat-id}/messages` — never `sendMail`
- Client: our `graph` package only. No Graph SDK.

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

**Do not** put the person’s real SMTP address in `From` or `Reply-To`. Entourage 2008 replies to `From`/`Reply-To` and sometimes drops custom `X-` headers; the special address is the durable map.

**Outbound route** (`OutboundRouter`, scanner — not smtpd):

1. `In-Reply-To` or `References` matches a `TossedMessage.message_id` with `source=teams` → chat post
2. Else any `To`/`Cc` is `teams.{chat_b32}@o365pop.local` → decode → chat post
3. Else `sendMail`
4. Any `@o365pop.local` that does not decode → `spool/failed/`, **never** `sendMail`

Chat post body = text before the first quoted block (`>`, `From:`, `-----Original Message-----`). Log if we fall back to the full body.

`ChatMap` row: `chat_id` ↔ `chat_b32` ↔ `reply_address` (one row per chat, reused for every message in that chat).

### Client-facing: POP3 + SMTP

- POP3 `:110` — **Twisted** `twisted.mail.pop3` over maildir. USER/PASS, STAT, LIST, RETR, DELE, UIDL, TOP, CAPA, QUIT. No APOP, no STLS. `popd` is its own process (Twisted reactor). Do not run it inside the aiosmtpd event loop.
- SMTP `:587` (optional `:25`) — EHLO, AUTH LOGIN, AUTH PLAIN, MAIL/RCPT/DATA. No STARTTLS, no XOAUTH2.
- Contract tests use a real `poplib` / `smtplib` client against the daemons.

### Inter-process

- Redis broker + result backend (taciturn2 default).
- Filesystem message base: maildir (inbound), spool (outbound).
- SQLite for account, sync sessions, tossed-index.

## 3. Code Organization

```
o365pop/                 # installable package (config, celery_app, cli, db)
  accounts/              # MailboxAccount, token helpers, device-code login
  graph/                 # GraphPort + HttpGraphAdapter
  tosser/                # inbound_tosser, outbound_scanner, mime_factory, router
  mailstore/             # MaildirStore, SpoolStore
  popd/                  # Twisted POP3 daemon (IMailboxPOP3 → maildir)
  smtpd/                 # aiosmtpd handler
  sync/                  # Celery tasks (pull, toss, scan, cleanup)
tests/{unit,integration,fixtures}
deploy/{Dockerfile,docker-compose.yml,libreelec/}
logs/app.log
docs/{architecture,features,plans}
```

Reuse **patterns** from taciturn2 (see Context Map in the plan). Do not vendor taciturn2 source.

## 4. Data Architecture

| Store | What |
|---|---|
| SQLite | `MailboxAccount`, `SyncSession`, `TossedMessage` (graph_id, source, message_id, chat_id, uidl), `ChatMap` (chat_id ↔ `teams.{b32}@o365pop.local`) |
| Maildir | RFC822 messages Entourage collects |
| Spool `new/` `retry/` `sent/` `failed/` | Outbound RFC822 from SMTP |
| Redis | Celery only — not a message store |
| Encrypted fields | Graph access + refresh tokens (Fernet, `TOKEN_ENCRYPTION_KEY`) |

Single `MailboxAccount` row in v1. POP UIDL = stable hash of Graph id (or generated id for synthesized Teams mail). `DELE` removes from maildir only; `TossedMessage` prevents re-toss and stores the RFC822 `Message-ID` used for reply routing.

## 5. Test Strategy

- pytest; layout `tests/unit/`, `tests/integration/`
- Unit: tosser, MIME factory, **reply router / chat address codec**, token encrypt, POP command parser, AUTH LOGIN decoder
- Integration: **no mocks**. Real maildir, real aiosmtpd, real POP daemon, real Celery eager, Graph via `FileGraphAdapter` (fixture JSON/MIME on disk) or a local HTTP fixture server — not `unittest.mock` on services
- Live Graph (device-code against Denis’s tenant) is lane 3 — not a PR merge gate
- Log-story tests (`assert_log_story`) for sync/toss/send decision beats
- Checkpoint: one pytest command per scenario (see plan)

## 6. Performance & Scalability

- One user, one worker (`prefetch=1`), beat every 2 minutes inbound / 30 seconds outbound
- Graph page size ≤ 50; respect `Retry-After`
- Soft time limit 10 minutes per sync (LibreELEC, not taciturn2’s 55-minute task dumps)

## 7. Error Handling & Resilience

Copy taciturn2 `sync_user_o365_data` shape:

- Auth failure: mark session failed, **do not retry** (avoids lockout loops)
- Graph 429: pause session, retry after `Retry-After` (or 120s)
- SoftTimeLimit: mark failed, return error dict
- Outbound send fail: leave message in `spool/retry/`; after N attempts move to `spool/failed/`
- Never delete Graph mail because POP `DELE` happened

## 8. Infrastructure

- Runtime: Docker on LibreELEC (`service.system.docker`), `--network host`
- Compose services: `redis`, `worker`, `beat`, `popd`, `smtpd`
- Persist `/storage/o365pop/{data,maildir,spool,logs}`
- Listen: `POP3_BIND` / `SMTP_BIND` (WireGuard IP). Default not `0.0.0.0` unless `ALLOW_LAN=1`

## 9. CI/CD Pipeline

v1: `make test` locally. GitHub Actions pytest later (BSP/DTA-10). No cloud deploy.

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
- `GRAPH_POLL_SECONDS`, `SPOOL_SCAN_SECONDS`

## 13. Security

- WireGuard encrypts the client hop. POP/SMTP are intentionally cleartext **inside** the tunnel.
- Do not bind 110/587 on the public NIC.
- Local mailbox password ≠ Microsoft password.
- Tokens encrypted at rest. Device-code login over SSH, not a browser on LibreELEC.
- Entourage must not be given the Azure password.

## 14. Backup & Recovery

Back up `/storage/o365pop/data` (SQLite + tokens) and maildir. Spool `failed/` is operator-visible. Token loss ⇒ device-code login again.

## 15. Developer Experience

- `make provision` `make test` `make worker` `make beat` `make popd` `make smtpd` `make login`
- pytest + Celery `task_always_eager` in unit/integration
- Dr. Dobbs v2: skeleton → red → green → refactor; methods ≤ 30 lines

## 16. Documentation Strategy

- This SAO is the architecture lock
- Feature files in `docs/features/act-*/`
- Plan in `docs/plans/O365POP_IMPLEMENTATION_PLAN.md`
- Update `_ai-context.mdc` when SAO sections change

## Technology Stack Table

| Layer | Choice |
|---|---|
| Language | Python 3.14 |
| App | Plain Python package + `python -m o365pop` CLI |
| Jobs | Celery + Redis (taciturn2 pattern) |
| Graph | `httpx` + `msal` |
| SMTP server | `aiosmtpd` |
| POP server | **Twisted** `twisted.mail.pop3` + `MaildirMailbox` |
| Message base | stdlib `mailbox.Maildir` |
| DB | SQLite |
| Deploy | Docker Compose, host network, LibreELEC |

## SAO sections that govern implementation

- §1 Application Blocks — daemon vs tosser split
- §2 Integration — Graph REST + POP/SMTP dialect
- §3 Code Organization
- §4 Data Architecture — tossed-index, local DELE
- §5 Test Strategy — no mocks in integration
- §7 Error Handling — taciturn2 sync failure shape
- §8 Infrastructure — LibreELEC / WireGuard binds
- §11 Observability — log story
- §13 Security — WG is the crypto; no Azure password on POP

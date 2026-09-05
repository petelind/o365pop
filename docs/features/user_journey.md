# o365pop User Journey

## Personas

**Denis** — Operator  
Runs o365pop as a Docker stack on LibreELEC. Has WireGuard inbound. Signs in to Microsoft once via device code over SSH. Reads `logs/app.log` when mail does not appear.

**Vintage Client** — Entourage 2008 (and other POP/SMTP clients)  
Lives on a Mac that reaches LibreELEC only through WireGuard (or LAN). Speaks POP3 on 110 and SMTP on 587 with no SSL. Uses a local mailbox password, not the Microsoft password.

---

## System Architecture Note

**o365pop**: local Graph-to-POP/SMTP bridge.

- **Celery worker + beat**: Graph pull, inbound toss, outbound scan (taciturn2 sync shape)
- **popd / smtpd**: wire protocols only; filesystem message base
- **Graph REST**: mail MIME + Teams chats + MIME send

**Domain model**:

- **MailboxAccount** — one Graph identity + local POP/SMTP credential
- **TossedMessage** — Graph id already dropped into maildir (dedup)
- **SyncSession** — one Celery pull/toss run
- **Maildir** — what POP serves
- **Spool** — what SMTP wrote and the scanner sends

---

## Critical Architectural Principle

**Daemons do not call Graph. Tosser does not speak POP/SMTP.**

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

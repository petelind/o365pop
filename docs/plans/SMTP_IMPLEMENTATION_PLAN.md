# SMTP — Implementation Plan

**Feature**: SMTP Entourage submits mail; scanner sends via Graph  
**Feature File**: `docs/features/act-1-bridge/smtp.feature`  
**Scenarios**: SMTP1.1, SEND1.1, SEND1.2  
**GitHub Issues**: none yet  
**Branch**: `feature/smtpd-sendmail`  
**Agent**: Dr. Dobbs v2  
**Prerequisites**: AUTH + SYNC (bearer, GraphPort.send_mime, FileGraphAdapter)

BPE-01 adjustments: `aiosmtpd` daemon + Celery scanner. smtpd must not import graph. TEAM router is **not** in this feature — SEND1.1 is always `sendMail`. TEAM adds the branch later.

---

## Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/features/act-1-bridge/smtp.feature` | 1–36 | SMTP1.1, SEND1.1–1.2 |
| `docs/architecture/SAO.md` | §1, §2 | smtpd writes spool; tosser/scanner calls Graph |
| `o365pop/graph/` | (SYNC) | `send_mime` — implement body here if still stubbed |
| `o365pop/accounts/store.py` | (AUTH) | AUTH LOGIN uses local password |
| `o365pop/sync/tasks.py` | (SYNC) | Add `scan_outbound_spool`; do not fold send into `sync_mailbox` |

---

## Do Not Do

- Do NOT import `graph` from `smtpd`
- Do NOT enable STARTTLS or XOAUTH2
- Do NOT implement Teams routing here (TEAM1.*) — all successful scans are `sendMail`
- Do NOT post chat messages
- Do NOT log full MIME bodies (log size + subject only)
- Do NOT use the Microsoft password for AUTH LOGIN

---

## SAO.md Sections That Apply

- §1 Application Blocks — smtpd vs scanner split
- §2 Integration — AUTH LOGIN, MIME sendMail
- §4 Data Architecture — spool `new/retry/sent/failed`
- §7 Error Handling — retry then failed
- §11 Observability
- §13 Security

---

## Current State Assessment

**Exists:** GraphPort stub `send_mime`, local account, Celery.  
**Missing:** aiosmtpd handler, SpoolStore, outbound scanner, beat for spool.

---

## Clarifications

None. TEAM comes next and will wrap the scanner with `OutboundRouter`. Keep `scan_once` a single function TEAM can extend.

---

## Implementation Plan

Rules: `do-skeletons-first`, `do-test-first`, `do-not-mock-in-integration-tests`, `do-assert-log-story`

### SMTP1.1 Spool from AUTH LOGIN + DATA

- [ ] **1.1** Skeleton `mailstore.SpoolStore` (`new`/`retry`/`sent`/`failed`)
- [ ] **1.2** Skeleton `smtpd.handler.BridgeHandler` — AUTH LOGIN/PLAIN, no STARTTLS, write `spool/new/`
- [ ] **1.3** Red: `tests/integration/test_smtp_spool.py` — real `smtplib`, no TLS, subject `Hello Ada`, Graph unused
- [ ] **1.4** Green
- **Commit**: `feat(smtpd): cleartext AUTH LOGIN writes RFC822 to spool`

### SEND1.1 Scanner → sendMail

- [ ] **2.1** Implement `HttpGraphAdapter.send_mime` / FileGraphAdapter records posted bytes
- [ ] **2.2** Skeleton `tosser.OutboundScanner.scan_once` — send then move to `sent`
- [ ] **2.3** `sync.tasks.scan_outbound_spool` + beat `SPOOL_SCAN_SECONDS` (default 30)
- [ ] **2.4** Red/green: `tests/integration/test_outbound_send.py` — same MIME bytes posted; file in `spool/sent`; log `exit` sent=1
- **Commit**: `feat(tosser): scan spool and POST MIME sendMail`

### SEND1.2 Graph reject → retry → failed

- [ ] **3.1** Attempt counter on spool sidecar or filename
- [ ] **3.2** Red: `tests/integration/test_outbound_send_fail.py` — HTTP 400 → `retry` then `failed`; log `error` reason=`send_failed`
- [ ] **3.3** Green
- **Commit**: `fix(tosser): retry then quarantine failed sendMail`

**Checkpoint**: `pytest tests/integration/test_smtp_spool.py tests/integration/test_outbound_send.py tests/integration/test_outbound_send_fail.py -x`

---

## Tests (explicit)

| Test | Proves |
|---|---|
| `test_smtp_spool` | SMTP1.1; Graph unused |
| `test_outbound_send` | SEND1.1 |
| `test_outbound_send_fail` | SEND1.2 |

---

## Definition of Done

- [ ] Checkpoint green
- [ ] `rg "from o365pop.graph" o365pop/smtpd` is empty
- [ ] Next feature is TEAM (router)

---

## Lessons Learned

*(fill during execute)*

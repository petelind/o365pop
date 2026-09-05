# POP — Implementation Plan

**Feature**: POP Entourage collects mail without TLS  
**Feature File**: `docs/features/act-1-bridge/pop.feature`  
**Scenarios**: POP1.1, POP1.2, POP1.3  
**GitHub Issues**: none yet  
**Branch**: `feature/popd-twisted`  
**Agent**: Dr. Dobbs v2  
**Prerequisites**: SYNC checkpoint green (maildir + TossedMessage + local password on MailboxAccount)

BPE-01 adjustments: Twisted POP3 daemon, not Django. Integration tests use stdlib `poplib` against a real listener.

---

## Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/features/act-1-bridge/pop.feature` | 1–32 | POP1.1–1.3 |
| `docs/architecture/SAO.md` | §2 Client-facing POP3 | Twisted `twisted.mail.pop3`, no STLS/APOP |
| `o365pop/mailstore/` | (SYNC) | MaildirStore — POP reads this; do not invent a second store |
| `o365pop/accounts/store.py` | (AUTH) | Local USER/PASS — not the Microsoft password |
| Twisted `twisted.mail.pop3.Mailbox` / `IMailboxPOP3` | API | Implement mailbox adapter; do not rewrite the protocol |

---

## Do Not Do

- Do NOT write a custom asyncio POP server
- Do NOT import `graph` from `popd`
- Do NOT enable TLS/STLS/APOP/XOAUTH2
- Do NOT delete Graph rows or call Graph on DELE
- Do NOT delete `TossedMessage` on DELE (prevents re-toss)
- Do NOT log the mailbox password
- Do NOT bind `0.0.0.0` in tests (use `127.0.0.1`)

---

## SAO.md Sections That Apply

- §1 Application Blocks — popd reads mailstore only
- §2 Integration — POP dialect
- §4 Data Architecture — local DELE
- §8 Infrastructure — bind (defaults; DEP locks WG)
- §11 Observability
- §13 Security

---

## Current State Assessment

**Exists after SYNC:** maildir with tossed RFC822, TossedMessage, local account password.  
**Missing:** Twisted reactor process, IMailbox adapter, USER/PASS, command coverage.

---

## Clarifications

None. Twisted locked. Cleartext on purpose.

---

## Implementation Plan

Rules: `do-skeletons-first`, `do-test-first`, `do-informative-logging`, `do-not-mock-in-integration-tests`

### POP1.1 List and retrieve

- [ ] **1.1** Skeleton `popd.mailbox.MaildirPopMailbox` implementing `IMailboxPOP3` (`listMessages`, `getMessage`, `getUidl`, `deleteMessage`, `sync`, `undeleteMessages`)
- [ ] **1.2** Skeleton `popd.service` — Twisted `POP3` factory, portal/checker against `MailboxAccount`
- [ ] **1.3** Red: `tests/integration/test_pop_retrieve.py` — real `poplib` on 127.0.0.1:11110; USER/PASS; STAT=1; UIDL; RETR has Subject; TOP 1 0 headers only
- [ ] **1.4** Green: no TLS on the transport
- **Commit**: `feat(popd): twisted POP3 STAT LIST RETR UIDL TOP`

### POP1.2 Wrong password

- [ ] **2.1** Red: `tests/integration/test_pop_auth.py` — PASS wrong → -ERR; RETR not allowed
- [ ] **2.2** Log story beat `error` reason=`auth_failed`; password absent from `caplog`
- **Commit**: `feat(popd): reject bad USER/PASS without logging secret`

### POP1.3 DELE local only

- [ ] **3.1** Red: `tests/integration/test_pop_dele_local_only.py` — DELE+QUIT removes maildir file; TossedMessage remains; GraphPort unused (do not inject a Graph client)
- [ ] **3.2** Green: `deleteMessage` + `sync` on QUIT
- **Commit**: `feat(popd): DELE removes maildir only`

**Checkpoint**: `pytest tests/integration/test_pop_retrieve.py tests/integration/test_pop_auth.py tests/integration/test_pop_dele_local_only.py -x`

---

## Tests (explicit)

| Test | Proves |
|---|---|
| `test_pop_retrieve` | POP1.1 dialect, no TLS |
| `test_pop_auth` | POP1.2 + log story |
| `test_pop_dele_local_only` | POP1.3 Graph unused |

---

## Definition of Done

- [ ] Checkpoint green
- [ ] `rg "from o365pop.graph" o365pop/popd` is empty
- [ ] Next feature is SMTP

---

## Lessons Learned

*(fill during execute)*

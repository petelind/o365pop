# SYNC — Implementation Plan

**Feature**: SYNC Inbound Graph pull and toss into maildir  
**Feature File**: `docs/features/act-1-bridge/inbound.feature`  
**Scenarios**: SYNC1.1, SYNC1.2, SYNC1.3  
**GitHub Issues**: none yet  
**Branch**: `feature/sync-inbound-toss`  
**Agent**: Dr. Dobbs v2  
**Prerequisites**: AUTH checkpoint green

BPE-01 adjustments: Graph is `httpx` + `GraphPort`; tests use `FileGraphAdapter` (real files, no `unittest.mock` on tosser). SYNC1.2 mints the Teams reply map (TEAM consumes it).

---

## Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/features/act-1-bridge/inbound.feature` | 1–38 | SYNC1.1–1.3 |
| `docs/architecture/SAO.md` | §2 Teams reply map | From/Reply-To/Message-ID mint — implement here, not in TEAM |
| `../taciturn2/api/tasks/sync_tasks.py` | 15–145 | Session running → work → completed; timeout/auth/generic mapping |
| `o365pop/accounts/graph_auth.py` | (AUTH) | `ensure_bearer` only — do not reimplement MSAL |
| `o365pop/sync/tasks.py` | (AUTH stub) | **Extend** the auth-only `sync_mailbox`; do not create a second task |

---

## Do Not Do

- Do NOT use the Microsoft Graph SDK or taciturn2/microsoft-mcp clients
- Do NOT put a person’s real SMTP address on tossed Teams From/Reply-To
- Do NOT call Graph from popd/smtpd (those do not exist yet; do not start them here)
- Do NOT delete Graph messages
- Do NOT mock `InboundTosser` or `MaildirStore` in integration tests
- Do NOT implement outbound sendMail or Teams reply routing (TEAM/SMTP)
- Do NOT write a custom POP server

---

## SAO.md Sections That Apply

- §1 Application Blocks — tosser owns Graph→maildir
- §2 Integration — Graph REST + Teams mint
- §3 Code Organization — `graph/`, `tosser/`, `mailstore/`, `sync/`
- §4 Data Architecture — TossedMessage, ChatMap, maildir
- §5 Test Strategy — FileGraphAdapter
- §7 Error Handling
- §11 Observability

---

## Current State Assessment

**Exists after AUTH:** bearer, sync_session, celery eager path.  
**Missing:** GraphPort, FileGraphAdapter, MaildirStore, tosser, ChatMap writes, full `sync_mailbox` pull+toss, beat schedule.

---

## Clarifications

None. Inbox + Teams into one maildir. Dedup by graph_id.

---

## Implementation Plan

Rules: `do-skeletons-first`, `do-test-first`, `do-not-mock-in-integration-tests`, `do-assert-log-story`, `do-write-concise-methods`

### Slice A — Graph port (SYNC prerequisite)

- [ ] **A.1** Skeleton `graph.GraphPort`: `list_inbox_messages`, `get_message_mime`, `list_new_chat_messages`, `send_mime`, `post_chat_message` (last two stubbed until SMTP/TEAM)
- [ ] **A.2** `FileGraphAdapter` reads `tests/fixtures/graph/<case>/`
- [ ] **A.3** `HttpGraphAdapter` (httpx) — unit-test URL construction with `httpx.MockTransport` (**unit only**)
- [ ] **A.4** Tests: `tests/unit/test_http_graph_adapter.py`, `tests/integration/test_file_graph_adapter.py`
- **Commit**: `feat(graph): GraphPort with httpx and file adapters`

### SYNC1.1 Outlook MIME toss

- [ ] **B.1** Skeleton `mailstore.MaildirStore` (add/list/get/uidl/delete)
- [ ] **B.2** Skeleton `tosser.InboundTosser.toss_outlook` + `TossedMessage` insert
- [ ] **B.3** Red: `tests/integration/test_inbound_toss_outlook.py` — fixture MIME subject `Q3 close`; second toss no dup
- [ ] **B.4** Green + log story `processing` tossed=1 skipped_dup=0
- **Commit**: `feat(tosser): toss Outlook MIME into maildir`

### SYNC1.2 Teams RFC822 + reply map mint

- [ ] **C.1** Skeleton `tosser.chat_address.encode/decode` and `ChatMap`
- [ ] **C.2** Skeleton `mime_factory.teams_to_rfc822`
- [ ] **C.3** Red: `tests/unit/test_chat_address.py`, `tests/unit/test_teams_mime_factory.py`
  - From is `teams.{b32}@o365pop.local`, not `ada@…`
  - Message-ID starts `<teams.`
  - Reply-To equals From
- [ ] **C.4** Red: `tests/integration/test_inbound_toss_teams.py` — SYNC1.2 on real maildir
- [ ] **C.5** Green
- **Commit**: `feat(tosser): synthesize Teams RFC822 with reply map`

### SYNC1.3 Empty sync + Celery wiring

- [ ] **D.1** Extend `sync_mailbox`: ensure_bearer → list inbox+chats → toss → mark completed
- [ ] **D.2** Beat entry `sync-mailbox` every `GRAPH_POLL_SECONDS` (default 120)
- [ ] **D.3** Failure mapping from taciturn2: timeout / auth / generic → failed, no retry on auth
- [ ] **D.4** Tests: `tests/integration/test_sync_mailbox_task.py` (SYNC1.1+1.2 via FileGraphAdapter); `tests/integration/test_sync_mailbox_empty.py` (SYNC1.3)
- **Commit**: `feat(sync): celery sync_mailbox pull and toss`

**Checkpoint**: `pytest tests/integration/test_inbound_toss_outlook.py tests/integration/test_inbound_toss_teams.py tests/integration/test_sync_mailbox_task.py tests/integration/test_sync_mailbox_empty.py -x`

---

## Tests (explicit)

| Test | Proves |
|---|---|
| `test_http_graph_adapter` | REST paths |
| `test_file_graph_adapter` | fixture load |
| `test_chat_address` | b32 roundtrip including `19:…@thread.v2` |
| `test_teams_mime_factory` | mint contract |
| `test_inbound_toss_outlook` | SYNC1.1 + dedup |
| `test_inbound_toss_teams` | SYNC1.2 |
| `test_sync_mailbox_task` | eager Celery pull+toss |
| `test_sync_mailbox_empty` | SYNC1.3 completed tossed=0 |

---

## Definition of Done

- [ ] SYNC1.1–1.3 checkpoint green
- [ ] ChatMap + Message-ID present so TEAM can route later
- [ ] `send_mime` / `post_chat_message` still unused by sync
- [ ] Next feature is POP

---

## Lessons Learned

*(fill during execute)*

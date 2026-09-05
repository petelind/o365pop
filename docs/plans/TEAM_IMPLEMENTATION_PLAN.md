# TEAM — Implementation Plan

**Feature**: TEAM Reply to a tossed Teams chat via SMTP  
**Feature File**: `docs/features/act-1-bridge/teams.feature`  
**Scenarios**: TEAM1.1, TEAM1.2, TEAM1.3, TEAM1.4  
**GitHub Issues**: none yet  
**Branch**: `feature/teams-reply-map`  
**Agent**: Dr. Dobbs v2  
**Prerequisites**: SYNC (ChatMap + minted Message-ID) and SMTP (`scan_outbound_spool`, SpoolStore)

BPE-01 adjustments: routing is tosser logic, not smtpd. smtpd still does not import graph.

---

## Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/features/act-1-bridge/teams.feature` | 1–39 | TEAM1.1–1.4 |
| `docs/architecture/SAO.md` | §2 Teams ↔ email reply map | Route order and fail-closed |
| `o365pop/tosser/mime_factory.py` | (SYNC) | Mint contract — do not change From to a real address |
| `o365pop/tosser/outbound_scanner.py` | (SMTP) | **Insert router here**; do not add a second scanner |
| `o365pop/graph/` | (SYNC) | Implement `post_chat_message` if still stubbed |

---

## Do Not Do

- Do NOT `sendMail` a message that maps to a Teams chat
- Do NOT `sendMail` any `@o365pop.local` address
- Do NOT put a real SMTP address on tossed Teams From/Reply-To (already minted in SYNC — do not regress)
- Do NOT implement routing inside smtpd
- Do NOT post the full quoted Entourage history if the top part extracts cleanly
- Do NOT mock OutboundRouter in integration tests

---

## SAO.md Sections That Apply

- §2 Teams ↔ email reply map (authoritative route order)
- §4 Data Architecture — ChatMap, TossedMessage.message_id
- §7 Error Handling — map miss → failed
- §11 Observability — beat `branch` route=`teams_chat`

---

## Current State Assessment

**Exists after SYNC+SMTP:** minted Teams RFC822, ChatMap, scanner always sendMail.  
**Missing:** OutboundRouter, reply-text extract, `post_chat_message`, fail-closed path.

---

## Clarifications

None. Q8 locked. Encode is lowercase base32, no padding.

---

## Implementation Plan

Rules: `do-skeletons-first`, `do-test-first`, `do-assert-log-story`, `do-not-mock-in-integration-tests`, `do-update-tests-after-bugfixing`

### TEAM1.1 In-Reply-To → chat

- [ ] **1.1** Skeleton `tosser.reply_text.extract` and `tosser.outbound_router.OutboundRouter.route`
- [ ] **1.2** Implement `GraphPort.post_chat_message` on FileGraphAdapter + HttpGraphAdapter
- [ ] **1.3** Red: `tests/unit/test_reply_text.py` — strips `>` / `From:` / `-----Original Message-----`
- [ ] **1.4** Red: `tests/unit/test_outbound_router.py` — In-Reply-To hits TossedMessage → `teams_chat`
- [ ] **1.5** Wire scanner: route then `post_chat_message` or `send_mime`
- [ ] **1.6** Red/green: `tests/integration/test_teams_reply_in_reply_to.py` — TEAM1.1; no sendMail; log `branch` route=`teams_chat`
- **Commit**: `feat(tosser): route In-Reply-To Teams replies to chat post`

### TEAM1.2 To address map (no In-Reply-To)

- [ ] **2.1** Red: unit + `tests/integration/test_teams_reply_to_address.py`
- [ ] **2.2** Green: To `teams.{b32}@o365pop.local` → ChatMap
- **Commit**: `feat(tosser): route teams.* To address when In-Reply-To missing`

### TEAM1.3 Ordinary mail unchanged

- [ ] **3.1** Red/green: `tests/integration/test_teams_reply_ordinary_mail.py` — ada@example.com still sendMail; no chat POST
- [ ] **3.2** Re-run SMTP SEND1.1 tests — no regression
- **Commit**: `test(tosser): ordinary sendMail still wins without Teams map`

### TEAM1.4 Unknown o365pop.local fail-closed

- [ ] **4.1** Red/green: `tests/integration/test_teams_map_miss.py` — Graph unused; retry then `failed`; log `error` reason=`teams_map_miss`
- **Commit**: `feat(tosser): fail closed on unknown teams.* address`

**Checkpoint**: `pytest tests/unit/test_outbound_router.py tests/unit/test_reply_text.py tests/integration/test_teams_reply_in_reply_to.py tests/integration/test_teams_reply_to_address.py tests/integration/test_teams_reply_ordinary_mail.py tests/integration/test_teams_map_miss.py -x`

---

## Tests (explicit)

| Test | Proves |
|---|---|
| `test_reply_text` | quote strip |
| `test_outbound_router` | decision table TEAM1.1–1.4 |
| `test_teams_reply_in_reply_to` | TEAM1.1 |
| `test_teams_reply_to_address` | TEAM1.2 |
| `test_teams_reply_ordinary_mail` | TEAM1.3 |
| `test_teams_map_miss` | TEAM1.4 |

---

## Definition of Done

- [ ] Checkpoint green
- [ ] SMTP SEND tests still green
- [ ] Next feature is DEP

---

## Lessons Learned

*(fill during execute)*

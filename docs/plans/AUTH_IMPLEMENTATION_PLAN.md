# AUTH — Implementation Plan

**Feature**: AUTH Device-code login and token refresh  
**Feature File**: `docs/features/act-1-bridge/auth.feature`  
**Scenarios**: AUTH1.1, AUTH1.2, AUTH1.3  
**GitHub Issues**: none yet  
**Branch**: `feature/auth-device-code`  
**Agent**: Dr. Dobbs v2  
**Prerequisites**: BOOT checkpoint green

BPE-01 adjustments: CLI instead of Django views; no frontend; AUTH1.3 uses a minimal Celery task that only performs auth (full toss comes in SYNC).

---

## Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/features/act-1-bridge/auth.feature` | 1–32 | Scenarios to prove |
| `../taciturn2/authentication/models.py` | 127–264 | Fernet get/set access + refresh; never log token material — **port, do not import** |
| `../taciturn2/authentication/services/azure_auth.py` | 105–152, 297–321 | Refresh + bearer headers — rewrite as public-client device code |
| `../taciturn2/api/tasks/sync_tasks.py` | 126–134 | Auth fail → failed session, **no retry** |
| `o365pop/db.py` | (BOOT) | sqlite; add account helpers here, do not invent a second store |

---

## Do Not Do

- Do NOT use a confidential-client / redirect URI flow (LibreELEC has no browser)
- Do NOT store the Microsoft password
- Do NOT log access token, refresh token, or device code
- Do NOT call Graph mail/chat APIs (AUTH is token only; `/me` for validate is allowed)
- Do NOT retry Celery on `AuthenticationError`
- Do NOT add Django User
- Do NOT implement inbound toss or POP/SMTP

---

## SAO.md Sections That Apply

- §2 Integration — MSAL public client, device-code, scopes
- §4 Data Architecture — encrypted token fields
- §7 Error Handling — auth fail does not retry
- §11 Observability
- §12 Config & Secrets
- §13 Security

---

## Current State Assessment

**Exists after BOOT:** sqlite schema stub, celery app, logging.  
**Missing:** `mailbox_account` row helpers, Fernet vault, `GraphAuthService`, CLI login, AUTH1.3 session failure path.

---

## Clarifications

None. Single mailbox. Device code. `TOKEN_ENCRYPTION_KEY` required.

---

## Implementation Plan

Rules: `do-skeletons-first`, `do-test-first`, `do-informative-logging`, `do-assert-log-story`, `do-write-concise-methods`, `do-import-on-module-level`

### AUTH1.1 Device-code login

- [ ] **1.1** Skeleton `accounts.store.MailboxAccount` + Fernet helpers (docstrings, types, `NotImplementedError`)
- [ ] **1.2** Red: `tests/unit/test_mailbox_account_tokens.py`
  - encrypt roundtrip
  - column is not plaintext
  - empty token clears field
- [ ] **1.3** Green: persist one row in sqlite
- [ ] **1.4** Skeleton `accounts.graph_auth.GraphAuthService.login_device_code`
- [ ] **1.5** Red/green: `tests/integration/test_auth_login.py` — MSAL via a **local fixture adapter** (`DeviceCodePort`) that returns tokens for `denis@example.com` (not live Microsoft in CI)
- [ ] **1.6** CLI `python -m o365pop login` calls the service
- [ ] **1.7** Log story AUTH1.1: beat `exit` user=`denis@example.com`; assert token strings absent
- **Commit**: `feat(auth): device-code login and encrypted token vault`

### AUTH1.2 Refresh expired access token

- [ ] **2.1** Skeleton `ensure_bearer(account)` / `refresh_access_token`
- [ ] **2.2** Red: `tests/unit/test_graph_auth_service.py` — expired access + valid refresh → new token stored, expiry in the future
- [ ] **2.3** Green: public-client `acquire_token_by_refresh_token` behind `MsalPort` (fixture in tests)
- [ ] **2.4** Log beats `entry` / `exit` on refresh; no token material
- **Commit**: `feat(auth): refresh expired Graph access token`

### AUTH1.3 Revoked refresh fails without retry

- [ ] **3.1** `AuthenticationError`; `sync_session` row helpers (`pending`/`running`/`failed`)
- [ ] **3.2** Minimal `sync.tasks.sync_mailbox` — `ensure_bearer` only; on `AuthenticationError` mark failed and **return** (do not `raise` / retry)
- [ ] **3.3** Red/green: `tests/integration/test_auth_revoked.py` — eager Celery; revoked refresh; session `failed`; task not re-enqueued
- [ ] **3.4** Log story: beat `error` reason=`auth_failed`
- **Commit**: `feat(auth): revoked refresh fails sync without retry`

**Checkpoint**: `pytest tests/unit/test_mailbox_account_tokens.py tests/unit/test_graph_auth_service.py tests/integration/test_auth_login.py tests/integration/test_auth_revoked.py -x`

---

## Tests (explicit)

| Test | Proves |
|---|---|
| `test_mailbox_account_tokens` | Fernet roundtrip; no plaintext |
| `test_graph_auth_service` | AUTH1.2 refresh |
| `test_auth_login` | AUTH1.1 store + log story, no secrets |
| `test_auth_revoked` | AUTH1.3 failed session, no retry |

---

## Definition of Done

- [ ] AUTH1.1–1.3 checkpoint green
- [ ] Methods ≤ 30 lines; Sphinx + types
- [ ] Log story in the same commit as behavior
- [ ] Next feature is SYNC

---

## Lessons Learned

*(fill during execute)*

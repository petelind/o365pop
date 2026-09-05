# o365pop — Program index

**Agent**: Dr. Dobbs v2  
**Process**: BPE-01 Plan Feature per feature (stack-adjusted: no Django, no UI, no Playwright)  
**Clarifications**: `docs/plans/O365POP_Clarifications.md`  
**SAO**: `docs/architecture/SAO.md`

Do not implement a feature until that feature’s plan is approved and its prerequisite checkpoint is green. One feature at a time. After each slice: test → commit (Angular) → then next slice.

GitHub issues: create after `git init`, one issue per plan below, body = that plan’s Context Map + Do Not Do + SAO sections + checkpoint (BPE-01 Step 10). Repo is not initialized yet.

---

## Execution order

| # | Plan | Feature file | Checkpoint |
|---|---|---|---|
| 0 | [BOOT_IMPLEMENTATION_PLAN.md](BOOT_IMPLEMENTATION_PLAN.md) | — | `pytest tests/unit/test_package_imports.py tests/unit/test_logging_configured.py tests/unit/test_db_schema.py tests/unit/test_celery_app.py -x` |
| 1 | [AUTH_IMPLEMENTATION_PLAN.md](AUTH_IMPLEMENTATION_PLAN.md) | `auth.feature` | `pytest tests/unit/test_mailbox_account_tokens.py tests/unit/test_graph_auth_service.py tests/integration/test_auth_login.py tests/integration/test_auth_revoked.py -x` |
| 2 | [SYNC_IMPLEMENTATION_PLAN.md](SYNC_IMPLEMENTATION_PLAN.md) | `inbound.feature` | `pytest tests/integration/test_inbound_toss_outlook.py tests/integration/test_inbound_toss_teams.py tests/integration/test_sync_mailbox_task.py tests/integration/test_sync_mailbox_empty.py -x` |
| 3 | [POP_IMPLEMENTATION_PLAN.md](POP_IMPLEMENTATION_PLAN.md) | `pop.feature` | `pytest tests/integration/test_pop_retrieve.py tests/integration/test_pop_auth.py tests/integration/test_pop_dele_local_only.py -x` |
| 4 | [SMTP_IMPLEMENTATION_PLAN.md](SMTP_IMPLEMENTATION_PLAN.md) | `smtp.feature` | `pytest tests/integration/test_smtp_spool.py tests/integration/test_outbound_send.py tests/integration/test_outbound_send_fail.py -x` |
| 5 | [TEAM_IMPLEMENTATION_PLAN.md](TEAM_IMPLEMENTATION_PLAN.md) | `teams.feature` | `pytest tests/unit/test_outbound_router.py tests/unit/test_reply_text.py tests/integration/test_teams_reply_in_reply_to.py tests/integration/test_teams_reply_to_address.py tests/integration/test_teams_reply_ordinary_mail.py tests/integration/test_teams_map_miss.py -x` |
| 6 | [DEP_IMPLEMENTATION_PLAN.md](DEP_IMPLEMENTATION_PLAN.md) | `deploy.feature` | `pytest tests/unit/test_bind_config.py -x` then `pytest tests/ -x` |

---

## Stack (locked)

Python 3.14 package · sqlite3 · Celery+Redis · httpx+msal · cryptography/Fernet · aiosmtpd · **Twisted POP3** · stdlib maildir · pytest

No Django. No Graph SDK. No custom asyncio POP.

---

## Global Do Not Do

Copied onto every feature plan as applicable:

- Do NOT import taciturn2 / microsoft-mcp Graph clients
- Do NOT call Graph from popd or smtpd
- Do NOT require TLS on POP/SMTP
- Do NOT bind 110/587 on the WAN NIC
- Do NOT log tokens or mailbox passwords
- Do NOT delete Graph mail on POP DELE
- Do NOT `sendMail` a Teams-mapped reply
- Do NOT put a real SMTP address on tossed Teams From/Reply-To

---

## BPE-01 adjustments (this stack)

| Template said | We do |
|---|---|
| Django models / admin | sqlite3 + `schema.sql` |
| Django views / HTMX / Playwright | CLI + `poplib`/`smtplib` integration tests |
| Frontend slices | omitted |
| Time estimates | omitted |
| GitHub issue per feature | after git init |

Every public method: Dr. Dobbs checklist (Sphinx, types, validate, log beats, ≤30 lines, tests first).

---

## Approval

Approve **BOOT** to start coding. Later features stay planned until you say to execute the next plan.

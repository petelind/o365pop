# Step Library Catalog (TFK-03)

Gherkin in `docs/features/act-1-bridge/` is the requirements document. There is **no behave runner**. Each phrase is proven by a pytest module (or a shared helper those tests call).

TFK-07 adds a row when a new scenario lands. Do not invent Gherkin steps for log beats — use `assert_log_story`.

## Shared helpers

| Phrase family | Helper | Notes |
|---|---|---|
| Isolated data dir, sqlite, maildir, spool | `tests/support/mailbox.py` → `mailbox_sandbox` | Session-safe tmp paths |
| Graph Inbox / chats / MIME on disk | `tests/support/fixtures.py` → `load_graph_case` | FileGraphAdapter input |
| RFC822 bytes | `tests/support/fixtures.py` → `load_mail` | POP/SMTP/tosser |
| Log beats | `tests/support/log_story.py` → `assert_log_story` | Same commit as behavior |
| TOKEN_ENCRYPTION_KEY / env | pytest `monkeypatch` + `.env.example` names | Never commit secrets |
| Live captured login (device-code once) | `tests/support/live_session.py` → `ensure_captured_session` | `var/live-e2e/` gitignored; `@live_graph` only |

## AUTH (`auth.feature`)

| Scenario | Phrase (Then / When) | Pytest / helper |
|---|---|---|
| AUTH1.1 | device-code login; encrypted tokens; beat `exit` user= | `tests/integration/test_auth_login.py` |
| AUTH1.2 | expired access; refresh; sync continues | `tests/unit/test_graph_auth_service.py` |
| AUTH1.3 | revoked refresh; session `failed`; no retry; beat `error` | `tests/integration/test_auth_revoked.py` |

## SYNC (`inbound.feature`)

| Scenario | Phrase | Pytest / helper |
|---|---|---|
| SYNC1.1 | Inbox `AAMk-outlook-1` / subject `Q3 close`; no dup | `tests/integration/test_inbound_toss_outlook.py` + fixture `graph/SYNC1.1-outlook-q3-close` |
| SYNC1.2 | Teams From `teams.{b32}@o365pop.local`; Message-ID `<teams.` | `tests/integration/test_inbound_toss_teams.py` + `graph/SYNC1.2-teams-ship-it` |
| SYNC1.4 | Teams HTML body → multipart/alternative text/plain + text/html | `tests/integration/test_inbound_toss_teams.py` + `graph/SYNC1.4-teams-html` |
| SYNC1.3 | empty sync; session `completed`; tossed=0 | `tests/integration/test_sync_mailbox_empty.py` + `graph/SYNC1.3-empty` |

## POP (`pop.feature`)

| Scenario | Phrase | Pytest / helper |
|---|---|---|
| POP1.1 | USER/PASS, STAT, UIDL, RETR, TOP; no TLS | `tests/integration/test_pop_retrieve.py` + `mail/outlook-q3-close.eml` |
| POP1.2 | wrong password `-ERR`; password not logged | `tests/integration/test_pop_auth.py` |
| POP1.3 | DELE local only; TossedMessage remains; Graph unused | `tests/integration/test_pop_dele_local_only.py` |

## SMTP / SEND (`smtp.feature`)

| Scenario | Phrase | Pytest / helper |
|---|---|---|
| SMTP1.1 | AUTH LOGIN + DATA → `spool/new`; Graph not called by smtpd | `tests/integration/test_smtp_spool.py` + `mail/hello-ada.eml` |
| SEND1.1 | scanner `sendMail`; file → `spool/sent` | `tests/integration/test_outbound_send.py` (S5 in progress) |
| SEND1.2 | Graph 400 → retry then `spool/failed` | `tests/integration/test_outbound_send_fail.py` (S5) |

## TEAM (`teams.feature`)

| Scenario | Phrase | Pytest / helper |
|---|---|---|
| TEAM1.1 | In-Reply-To → chat post; route=`teams_chat` | `tests/integration/test_teams_reply_in_reply_to.py` (S6 skeleton) |
| TEAM1.2 | To `teams.{b32}@…` without In-Reply-To | `tests/integration/test_teams_reply_to_address.py` (S6 skeleton) |
| TEAM1.3 | ordinary To → sendMail | `tests/integration/test_teams_reply_ordinary_mail.py` (S6 skeleton) |
| TEAM1.4 | unknown `@o365pop.local` → failed; `teams_map_miss` | `tests/integration/test_teams_map_miss.py` (S6 skeleton) |

## DEP (`deploy.feature`)

| Scenario | Phrase | Pytest / helper |
|---|---|---|
| DEP1.1 | bind 110/587; not WAN; compose services | `tests/unit/test_bind_config.py` (S7 skeleton) |

## TASK (`tasks.feature`) — spec only until BPE-01

| Scenario | Phrase | Pytest / helper |
|---|---|---|
| TASK1.1 | snapshot task → Entourage Task + uid + Project + category | `tests/integration/test_task_snapshot_create.py` |
| TASK1.2 | missing To Do list → create Project | `tests/unit/test_task_project_map.py` (not written) |
| TASK1.3 | renamed list → rename Project | `tests/unit/test_task_project_map.py` (not written) |
| TASK1.4 | deleted list → delete synced Project | `tests/unit/test_task_project_map.py` (not written) |
| TASK1.5 | masterCategory color → Entourage category | `tests/unit/test_task_category_color.py` (not written) |
| TASK1.6 | Entourage completed → Graph PATCH | `tests/integration/test_task_receipt_patch.py` (not written) |
| TASK1.7 | untagged local task ignored | `tests/unit/test_task_receipt_ignore_local.py` (not written) |
| TASK1.8 | LibreELEC down; no raise; retry | `tests/unit/test_taskd_reachability_down.py` (not written) |

## Live journey (`docs/features/user_journey.md`) — `@live_graph` only

| Act | Phrase | Pytest / helper |
|---|---|---|
| Act 1 | device-code (or reuse vault); encrypted tokens; local USER/PASS | `tests/live/test_user_journey.py::test_act1_login_captured_for_real_user` |
| Act 2 | live sendMail probe → toss → POP RETR | `tests/live/test_user_journey.py::test_act2_sync_probe_then_pop_collect` |
| Act 3 | SMTP AUTH LOGIN → scanner sendMail → `spool/sent` | `tests/live/test_user_journey.py::test_act3_smtp_sendmail_to_self` |
| Act 4 | To `teams.*` → chat post (skip if no chats) | `tests/live/test_user_journey.py::test_act4_teams_reply_posts_chat` |
| Act 5 | To Do snapshot → Entourage Task (operator Mac) | live `taskd` on Entourage host — not `make test` |

`make test-e2e` / `make test-live-graph`. Not part of `make test`.

## BOOT (no feature file)

| Proof | Pytest |
|---|---|
| Package imports | `tests/unit/test_package_imports.py` |
| Log story golden | `tests/unit/test_logging_log_story_happy.py` |
| Schema / Celery | `tests/unit/test_db_schema.py`, `tests/unit/test_celery_app.py` |
| CLI health | `tests/unit/test_cli_status.py` |
| Fixture loaders | `tests/unit/test_fixture_library.py` |

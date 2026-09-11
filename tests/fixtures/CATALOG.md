# Fixture Library Catalog (TFK-04)

TFK-04 re-run 2026-09-05 (Edda v73, daemon-adjusted). Static cases live under `tests/fixtures/`. Loaders: `tests/support/fixtures.py`. Isolated dirs: `tests/support/mailbox.py`. No FactoryBoy — JSON presets + FileGraphAdapter.

JSON presets describe **shape**, not live secrets. Encrypted token columns stay null until AUTH tests write Fernet ciphertext.

## Graph cases (`graph/<case>/`)

| case_id | Path | Files | Linked scenario | Linked test |
|---|---|---|---|---|
| SYNC1.1-outlook-q3-close | `graph/SYNC1.1-outlook-q3-close/` | `inbox.json`, `message.eml` | SYNC1.1 | `tests/integration/test_inbound_toss_outlook.py` |
| SYNC1.2-teams-ship-it | `graph/SYNC1.2-teams-ship-it/` | `chats.json`, `messages.json` | SYNC1.2 | `tests/integration/test_inbound_toss_teams.py` |
| SYNC1.4-teams-html | `graph/SYNC1.4-teams-html/` | `chats.json`, `messages.json` | SYNC1.4 | `tests/integration/test_inbound_toss_teams.py` |
| SYNC1.3-empty | `graph/SYNC1.3-empty/` | `inbox.json`, `chats.json` | SYNC1.3 | `tests/integration/test_sync_mailbox_empty.py` |
| TASK1.1-q3-report | `graph/TASK1.1-q3-report/` | `lists.json`, `tasks.json`, `categories.json` | TASK1.1 | `tests/integration/test_publish_task_snapshot.py` |

`inbox.json` / `chats.json` / `messages.json` are Graph-like `{ "value": [ ... ] }` lists. MIME is raw RFC822 (`message.eml`). FileGraphAdapter (SYNC) must read these paths as-is.

## RFC822 (`mail/`)

| id | Path | Used by |
|---|---|---|
| outlook-q3-close | `mail/outlook-q3-close.eml` | SYNC1.1, POP1.1, POP1.3 |
| hello-ada | `mail/hello-ada.eml` | SMTP1.1, SEND1.1, TEAM1.3 |
| teams-ship-it | `mail/teams-ship-it.eml` | SYNC1.2, TEAM1.1 |

## Presets (`presets/`)

| id | Path | Scope | Notes |
|---|---|---|---|
| empty | `presets/empty.json` | isolation | no account, no tossed rows |
| authenticated_mailbox | `presets/authenticated_mailbox.json` | AUTH/SYNC Background | one mailbox_user=`denis`; token fields empty placeholders |

## Live vault (not a committed fixture)

`var/live-e2e/` — created by `ensure_captured_session`. Encrypted tokens + maildir/spool. Gitignored. Never commit.

## Agent eval roots

**N/A** (SAO §17 skipped). Do not add `llm_scripts/` or `agent_tasks/`.

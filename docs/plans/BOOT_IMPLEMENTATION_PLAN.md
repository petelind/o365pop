# BOOT — Implementation Plan

**Feature**: BOOT Scaffold package, Celery, SQLite, logging  
**Feature File**: none (prerequisite for all `act-1-bridge` features)  
**GitHub Issues**: none yet  
**Branch**: `feature/boot-scaffold`  
**Agent**: Dr. Dobbs v2  
**Prerequisites**: Plan approval; `git init`

BPE-01 adjustments: no Django apps, views, templates, HTMX, or Playwright. This slice is filesystem + pytest + logging only.

---

## Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/architecture/SAO.md` | §3, §11, stack table | Package layout, `logs/app.log`, no Django |
| `../taciturn2/taciturn/celery.py` | 1–40 | Celery app shape — port without `django.conf` |
| `../taciturn2/taciturn/settings.py` | 266–284, 310–337 | `acks_late`, prefetch=1, RotatingFileHandler → `logs/app.log` |
| `.cursor/agents/dr-dobbs-v2.md` | 75–95 | Skeleton → red → green; method checklist |

---

## Do Not Do

- Do NOT add Django, FastAPI, or any HTTP app
- Do NOT vendor taciturn2 source
- Do NOT implement Graph, tosser, popd, or smtpd in this feature
- Do NOT commit `.env`, encryption keys, or `*.sqlite3`
- Do NOT add hours/days

---

## SAO.md Sections That Apply

- §3 Code Organization
- §4 Data Architecture (schema exists; tables filled by later features)
- §11 Observability
- §12 Config & Secrets
- §15 Developer Experience

---

## Current State Assessment

**Exists:** package, pytest, Celery app, SQLite schema, `logs/app.log`, Makefile.  
**Python:** 3.14 (operator direction; SAO stack table updated from 3.12).  
**Missing:** AUTH feature; Redis only required for live worker/beat.

---

## Clarifications

None. Q2 locked: no Django.

---

## Implementation Plan

Rules each step: `do-skeletons-first`, `do-test-first`, `pytest`, `do-informative-logging`, `do-follow-commit-convention`, `do-small-increments`

### Scenario: BOOT1.1 Repo and package

- [x] **1.1** `git init`, `.gitignore` (`.env`, `.venv`, `__pycache__`, `*.sqlite3`, `var/`, `logs/*.log`)
- [x] **1.2** Package `o365pop/` with modules: `config.py`, `db.py`, `celery_app.py`, `cli.py`, `logging_setup.py`
- [x] **1.3** Module packages: `accounts`, `graph`, `tosser`, `mailstore`, `popd`, `smtpd`, `sync` (stubs only)
- [x] **1.4** `requirements.txt`: celery[redis], redis, httpx, msal, aiosmtpd, twisted, cryptography, pytest, pytest-asyncio
- [x] **1.5** `pytest.ini` writes `tests.log`; `tests/{unit,integration,fixtures,support}/`
- [x] **1.6** Makefile: `provision test worker beat popd smtpd login`
- **Test**: `tests/unit/test_package_imports.py` — `import o365pop` succeeds
- **Commit**: `chore(boot): init repo and package layout`

### Scenario: BOOT1.2 Logging

- [x] **2.1** Skeleton `configure_logging()` — docstring, `NotImplementedError`
- [x] **2.2** Red: `tests/unit/test_logging_configured.py` — handler writes INFO to `logs/app.log`; format includes `beat`
- [x] **2.3** Green: RotatingFileHandler; truncate/rotate on process start
- [x] **2.4** `tests/support/log_story.py` → `assert_log_story(...)`
- **Commit**: `feat(boot): rotating logs/app.log and log-story helper`

### Scenario: BOOT1.3 SQLite + Celery app

- [x] **3.1** `schema.sql` — tables `mailbox_account`, `sync_session`, `tossed_message`, `chat_map` (empty use until AUTH/SYNC)
- [x] **3.2** `db.connect()` / `db.init_schema()` — stdlib sqlite3
- [x] **3.3** `celery_app.py` — broker/backend from env; `acks_late=True`; `prefetch=1`; no Django
- [x] **3.4** Tests: `tests/unit/test_db_schema.py` (tables exist); `tests/unit/test_celery_app.py` (app name, acks_late)
- **Commit**: `feat(boot): sqlite schema and celery app`

**Checkpoint**: `pytest tests/unit/test_package_imports.py tests/unit/test_logging_configured.py tests/unit/test_db_schema.py tests/unit/test_celery_app.py -x`

---

## Definition of Done

- [x] Checkpoint green
- [x] No Django in `requirements.txt`
- [x] `make test` runs pytest
- [x] Public functions have Sphinx docstrings + types
- [x] Next feature is AUTH

---

## Lessons Learned

- BSP-07 Django welcome page does not apply: SAO forbids a web UI. Health is `python -m o365pop status`.
- BSP-08 `gui.log` / HTMX / token consumption logs do not apply (no frontend, no in-app LLM).
- Operator chose Python 3.14 over installing 3.12; stack lock updated in SAO.

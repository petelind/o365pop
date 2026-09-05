# TFK verification — daemon Trophy (Edda v73 re-run)

**Workflow:** Test Automation Framework (TFK-01 → TFK-09)
**Playbook:** Edda v73.0 (`.cursor/playbooks/edda/TFK/`)
**Date:** 2026-09-05
**Authority:** `docs/architecture/SAO.md` §5

Stock Edda Trophy assumes Django + behave + Playwright + optional agent lanes. o365pop is a headless mail bridge. This run **applies** TFK-01–05 against that SAO and **records skips** for stock AT/E2E/agent work.

---

## TFK-01 Define Test Architecture

SAO §5 fleshed: Trophy table, runner mapping, coverage, zero-bug, layout, Graph modes, log story, agent-lane skip.

Stock vs daemon mapping is in SAO §5. Pointer file: `docs/architecture/test-architecture.md`.

## TFK-02 Bootstrap Test Harness

```
tests/
  unit/ + integration/ + fixtures/ + support/
  support/log_story.py     ✅ assert_log_story (keyword + list forms)
  support/agent_story.py   skip (SAO §17 N/A)
  fixtures/llm_scripts/    skip
  fixtures/agent_tasks/    skip
  live/                    @live_graph operator journey (no Playwright)
docs/features/steps/       skip (no behave)
behave.ini                 skip
pytest.ini                 ✅ unit / integration / log_story / live_graph
```

Golden log-story test: `tests/unit/test_logging_log_story_happy.py`.

## TFK-03 Build Step Library

Catalog: `docs/features/CATALOG.md`. Phrases map to pytest modules, not behave steps.

TFK-07 adds a row when a new scenario lands. No Gherkin for log beats.

## TFK-04 Build Fixture Library

Catalog: `tests/fixtures/CATALOG.md`.

- Graph cases under `tests/fixtures/graph/<case>/`
- RFC822 under `tests/fixtures/mail/`
- Presets under `tests/fixtures/presets/`
- No FactoryBoy / AutoFixture (JSON + sandbox loaders)
- No `llm_scripts/` / `agent_tasks/`

## TFK-05 Wire CICD Integration

`.github/workflows/ci.yml` merge gate:

1. `make provision`
2. `make lint`
3. `make test-unit`
4. `make test-integration`

No `make test-at` (no behave). No staging E2E job. No `agent-eval.yml`.

Makefile no-ops (so stock TFK commands do not fail the operator):

- `make test-at` → skip: no behave AT
- `make test-e2e` → `pytest tests/live/ -m live_graph -s` (operator journey; not Playwright)
- `make test-agent-proof` / `test-agent-live` / `test-agent-quality` → skip: SAO §17 N/A

## TFK-06 Establish E2E Infrastructure

**Skip Playwright.** SAO §1: no web UI. Operator E2E is `tests/live/` + `@live_graph` (device-code capture, real popd/smtpd). Do not add Playwright, `tests/e2e/`, or `cd.yml` e2e-staging.

## TFK-07 Add Step and/or Fixture

**No catalog gap this run.** AUTH/SYNC/POP/SMTP1.1/TEAM/DEP phrases already have rows. SEND1.1 / SEND1.2 rows exist; tests are red until S5 scanner lands. Do not invent FactoryBoy or PRF scripts.

## TFK-08 Validate Test Health

| Level | Command | Result (2026-09-05) |
|-------|---------|---------------------|
| Lint | `make lint` | PASS |
| Unit | `make test-unit` | 37 passed, **5 failed** (`NotImplementedError`) |
| Log story | `make test-log-story` | PASS (BOOT golden) |
| Integration | `make test-integration` | Not a full green merge gate — SEND/TEAM/DEP still skeleton |
| AT | `make test-at` | skip |
| E2E | `make test-e2e` | live journey (`tests/live/`); skip if Azure env missing |

**CRITICAL (expected, tracked):**

| Test | Why | Issue |
|------|-----|-------|
| `test_bind_config.py` (2) | DEP `validate_bind` still NIE | #7 DEP |
| `test_outbound_router.py` (2) | TEAM router still NIE | #6 TEAM |
| `test_reply_text.py` (1) | TEAM reply extract still NIE | #6 TEAM |
| SEND1.1 / SEND1.2 integration | SMTP scanner not implemented | #5 SMTP |

**WARNING:** none new (no mock violations found in integration tests that already land).

**INFO:** Full `make test` stays red until S5–S7 skeletons are filled. Scenario checkpoints remain the MIN gate.

## TFK-09 Prepare Test Report

| Finding | Action | Priority |
|---------|--------|----------|
| DEP bind NIE | Implement S7; do not paper over tests | tracked #7 |
| TEAM router / reply-text NIE | Implement S6 | tracked #6 |
| SEND scanner NIE | Next slice S5 SEND1.1 | tracked #5 |
| Stock AT/E2E/agent missing | Documented skip — do not file | none |

No new GitHub issues. Coverage gaps are the remaining mail-bridge scenarios, not missing TFK infrastructure.

TFK re-run is complete.

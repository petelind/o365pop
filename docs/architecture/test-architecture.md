# Test architecture (pointer)

**Authority:** [`SAO.md` §5 Test Strategy](SAO.md#5-test-strategy).

This file exists so TFK/BPE agents can find the finished Test Strategy without hunting. Do not duplicate tables here — edit SAO §5.

| Asset | Path |
|---|---|
| Step / phrase catalog (TFK-03) | [`docs/features/CATALOG.md`](../features/CATALOG.md) |
| Fixture catalog (TFK-04) | [`tests/fixtures/CATALOG.md`](../../tests/fixtures/CATALOG.md) |
| Log-story helper (TFK-02) | `tests/support/log_story.py` → `assert_log_story` |
| Merge gate | `make test` (`pytest tests/ -m "not live_graph"`) |
| TFK run record | [`docs/process/TFK_VERIFICATION.md`](../process/TFK_VERIFICATION.md) |

**Skipped from stock TFK (documented drift):**

- behave-django / `docs/features/steps/` — no Django test client
- Playwright / `tests/e2e/` — no UI (SAO §1)
- Agent lanes / `assert_agent_story` — SAO §17 N/A

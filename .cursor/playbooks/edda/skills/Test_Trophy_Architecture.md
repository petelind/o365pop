# Test Trophy Architecture

**Capability**: Test Strategy & Design
**Stack**: testing-trophy, integration-testing

# Skill: Test Trophy Architecture

**Capability Domain**: TEST_STRATEGY
**Technology Stack**: pytest+behave

## Overview

Integration-first testing philosophy replacing the traditional test pyramid. The "trophy" shape reflects where we invest most: thick integration tests in the middle, thin unit tests at the base, acceptance tests above, and selective E2E at the top.

## The Test Trophy Model

```
        ╱╲          E2E (selective, slow, staging only)
       ╱────╲        Acceptance Tests (behave, BDD .features)
      ╱════════╲     INTEGRATION TESTS (main bet, no mocking)
     ╱──────────╲    Unit Tests (thin, only where isolation helps)
    ════════════════  Static Analysis (linting, type checks)
```

## Why Not the Pyramid?

1. **Unit tests have limited value**: Testing `model.save()` returns OK tells us nothing about whether data persisted.
2. **Acceptance tests are expensive**: Real browser, slow, flaky.
3. **Integration tests are the sweet spot**: Real objects, real connections, real data. Fast enough for CI, thorough enough to catch real bugs.

## When Unit Tests ARE Valuable

- Custom QuerySet methods with complex filtering logic
- Pure utility/helper functions with interesting edge cases
- Business logic methods that do computation (not just DB operations)

## When Unit Tests ARE NOT Valuable

- Default Model CRUD
- Auto-generated admin views
- Framework behavior
- Anything that requires mocking to test in isolation

## Agent test lanes (when SAO §17 applies)

When the project has in-app LLM agents, extend the Trophy with **four agent lanes** — still integration-first, still no domain mocks:

| Lane | Trophy layer | CI gate | Mock seam |
|------|--------------|---------|-----------|
| 1 Control-plane proofs | Integration (thick) | PR when `AGENTS_ENABLED=true` | CAP-004 ScriptedLLM only |
| 2 Deterministic shell | Integration (thick) | PR (normal integration) | None — no LLM |
| 3 Live contract eval | Integration / contract | Nightly / optional CD | Live provider, temp=0 |
| 4 Task performance quality | Eval overlay | Promotion band | Live provider + golden oracle |

**Placement:**
- Lanes 1–2 are part of the **integration band** — same real DB/services discipline as the Trophy main bet.
- Lane 3 is a **contract eval** overlay — schema and response bounds, not merge-blocking flake.
- Lane 4 is **outside PR merge** — TASK-* golden tasks; regression vs last certified band.

**Do not** move agent orchestration proofs to unit tests or Behave AT. User-visible AT stays in the acceptance band; PRF-* control-plane proofs stay in lane 1 pytest (`@agent_proof`).

See skill *Agent Integration Proof Patterns* (lane 1–2) and *Agent Task Eval* (lane 4).

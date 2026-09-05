# Agent Integration Proof Patterns

**Capability**: —
**Stack**: —

# Skill: Agent Integration Proof Patterns

**Capability Domain**: TEST_INTEGRATION
**Technology Stack**: pytest, CAP-004, artifact-56
**Linked Activities**: TFK-02, BPE-02, DTA-19

## Overview

Patterns for **lane 1** (control-plane proofs) and **lane 2** (deterministic shell) agent testing. Proves orchestration under **ScriptedLLM** — not model quality. Generic for any project with SAO §17 and selected PRF-* rows from artifact 56 Part 4.5.

## Principles

1. **Only CAP-004 mocks the LLM.** Real DB, real broker (if used), real tool registry.
2. **Assert the control plane, not chat prose.** Workflow id, tool names, domain writes, plan/step transitions, blackboard keys.
3. **Scripted queue = test oracle for LLM turns.** Temperature irrelevant in lane 1.
4. **Happy + reject** for adverse PRF rows (429, parse fail, HITL block, exhausted queue).

## Harness (TFK-02)

See rule `do-assert-agent-story` and TFK-02 for `assert_agent_story` and `@pytest.mark.agent_proof`.

## Lane 2 (deterministic shell)

Non-LLM steps are ordinary pytest — no `@agent_proof`, no ScriptedLLM.

## CI

Lane 1 via `make test-agent-proof` when `AGENTS_ENABLED=true`. Do not add `-m agent_proof` to default PR CI until PRF tests exist.

## Anti-patterns

FakeLLM silent fallback; `@patch` on ToolExecutor; asserting assistant wording.

## References

Artifact 56 Part 4.5; Rule `do-assert-agent-story`.

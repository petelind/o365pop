# Definition of Done Checklist Template

**Type**: Document
**Required**: No
**Produced by**: Generate AI IDE Configuration

# Definition of Done Checklist Template

**Artifact ID**: 43
**Type**: Template
**Required**: True

## Description

Reusable checklist template defining 'done' criteria for feature delivery: test coverage, logging, code quality, accessibility, documentation, deployment readiness, and (when SAO §17 applies) agent proof + TASK promotion gates. Created once during DSP process setup and consumed by all BPE iterations.

---

# {FeatureName} — Definition of Done

**Feature**: {FeatureScreenID} {FeatureTitle}
**GitHub Issue**: #{IssueNumber}
**Implementation Plan**: `{PlanPath}`

---

## Core Development Rules Checklist

### Test-First Development
- [ ] Every function/method has corresponding test(s)
- [ ] Feature files in `docs/features/` exist and comply with scenarios
- [ ] Tests use pytest framework
- [ ] Mocking is minimal (CAP-004 ScriptedLLM carve-out in `@agent_proof` tests only)

### Continuous Testing
- [ ] All tests are runnable via `pytest tests/`
- [ ] Tests are pytest compatible with proper fixtures
- [ ] `tests.log` file exists and contains test output

### Concise Methods
- [ ] Top-level (public) methods are 20-30 lines maximum
- [ ] Supporting logic is in well-named private methods
- [ ] Helper methods have single, focused responsibilities
- [ ] Method names are descriptive and clear

---

## Code Quality Rules Checklist

### Import Management
- [ ] All imports are at module level
- [ ] No imports inside functions/methods
- [ ] Dependencies are properly declared

### Log Story Verification
- [ ] Implementation plan / issue contains a **Log Story Script** (Where / Beat / Trigger / Must include)
- [ ] Every script row is proven by a passing `*_log_story_*` caplog test (or `checkpoint.log_story_command` from the iteration manifest)
- [ ] Happy **and** reject paths covered when the scenario has both
- [ ] Log levels are appropriate (DEBUG, INFO, WARNING, ERROR)
- [ ] No secrets/tokens/passwords appear at INFO in asserted lines
- [ ] No deferred logging slice remains in the plan

Grep of `logs/app.log` is an **audit aid**, not the DoD gate. Caplog (or `log_story_command`) is the gate.

### Agent Proof Verification (when SAO §17 / plan Section G in scope)
- [ ] Implementation plan / issue contains an **Agent Proof Table** (PRF ID, workflow, script path, trace beats)
- [ ] Every PRF row is proven by a passing `*_agent_story_*` test marked `@pytest.mark.agent_proof` (or `checkpoint.agent_proof_command` from the iteration manifest)
- [ ] Happy **and** reject paths covered when the PRF is adverse or has a reject sketch
- [ ] Tests use **CAP-004 ScriptedLLM** only — no `FakeLLM`, no `@patch` on ToolExecutor or domain services in `@agent_proof` tests
- [ ] LLM scripts exist under `tests/fixtures/llm_scripts/<prf-id>/` for every asserted path
- [ ] Trace asserts control-plane beats per artifact 56 Part 4.5 addendum: **workflow**, **tools**, **domain**, **board/plan** — not assistant wording
- [ ] No secrets/tokens/passwords in trace or asserted log lines
- [ ] No deferred agent-proof slice remains in the plan

Grep of run logs is an **audit aid**, not the DoD gate. `assert_agent_story` (or `agent_proof_command`) is the gate.

### TASK Promotion Checklist (lane 4 — when SAO §17 TASK-* rows selected; not story merge DoD)
- [ ] Golden task fixtures exist under `tests/fixtures/agent_tasks/<task-id>/` with `manifest.yaml` fields: `task_id`, `sc_xx`, `fixture_ref`, `oracle_type`, `pass_band`, `expected_ref`
- [ ] `n_runs` and certified pass band recorded in SAO §17 when task is promotion-gated
- [ ] Tests marked `@pytest.mark.quality` (+ `@live_llm` when using live provider); temp=0 on eval runs
- [ ] Structured oracle is source of truth — Deepeval overlay (if used) is secondary for SC-01 fuzzy tasks only
- [ ] `make test-agent-quality` green vs last certified band before human promotion decision
- [ ] Lane 4 failure does **not** block story merge when PRF lane 1 proofs are green — confirm TASK eval remains on nightly / promotion path only

---

## Testing and Quality Assurance Checklist

### Integration Test Standards
- [ ] Integration tests in `tests/integration/` exist
- [ ] Integration tests avoid mocking (except CAP-004 ScriptedLLM in `@agent_proof` tests)
- [ ] Real dependencies are used in integration scenarios

### Commit Conventions
- [ ] Recent commit messages follow Angular conventional format
- [ ] Commits are atomic and focused
- [ ] Breaking changes are documented in commit messages

---

## UI and Frontend Rules Checklist

### Django Views + HTMX
- [ ] No DRF views exist for new web UI features
- [ ] Django views return HTML templates
- [ ] HTMX attributes used for dynamic interactions
- [ ] Services layer is shared between MCP and Web UI

### Semantic Naming
- [ ] All interactive elements have `data-testid` attributes
- [ ] Naming follows kebab-case convention
- [ ] Form inputs have proper name and id attributes

---

## Documentation Checklist

### Scenario Writing
- [ ] BDD scenarios exist for features
- [ ] Feature files are well-structured
- [ ] Scenarios cover edge cases and error conditions
- [ ] Review GUI — do scenarios match behavior, fields, URLs, design rules?

### TODO Management
- [ ] TODO comments exist for incomplete implementations
- [ ] TODO items have clear descriptions
- [ ] TODOs in dependencies can be ignored

---

## Final Validation Checklist

### Overall Quality Check
- [ ] Feature meets acceptance criteria
- [ ] Code is production-ready
- [ ] Documentation exists and is accurate

### Integration Validation
- [ ] Feature integrates with existing system
- [ ] No breaking changes introduced
- [ ] Dependencies properly declared in requirements.txt

### Deployment Readiness
- [ ] Database migrations exist if needed
- [ ] Environment variables are documented
- [ ] Configuration changes are documented

### Cleanup
- [ ] Remove temporary files like debug_*.py
- [ ] Scan file structure for stray misplaced files
- [ ] Remove *.log files from repository

---

## Rules Reference

Before validating DoD, **read** each Rule below in this playbook (by slug), then **apply** it:

Required:
- `do-test-first`
- `do-continuous-testing`
- `do-write-concise-methods`
- `do-import-on-module-level`
- `do-informative-logging`
- `do-assert-log-story`
- `do-assert-agent-story` (when SAO §17 / Section G in scope)
- `do-not-mock-in-integration-tests`
- `do-follow-commit-convention`
- `do-semantic-versioning-on-ui-elements`
- `pytest`

Activity-specific:
- Observability DoD is **Log Story Verification** (caplog / `log_story_command`), not "logging statements exist".
- Agent DoD is **Agent Proof Verification** (`agent_proof_command` / `@agent_proof`), not "the agent loop exists" or Behave AT alone.
- TASK-* lane 4 is **Promotion Checklist** only — artifact 56 Part 4.6; skill *Agent Task Eval*.

---

## Sign-off

- [ ] All applicable checklist items verified
- [ ] Deviations documented and approved (or deferred as GitHub issues with `deferred` label)
- [ ] Ready for PR / merge

**Reviewer**: {ReviewerName}
**Date**: {SignOffDate}

---

## Placeholder Reference

- `{FeatureName}` — Feature name
- `{FeatureScreenID}` — Screen ID (e.g., FOB-AUTH-LOGIN-1)
- `{IssueNumber}` — GitHub issue number
- `{PlanPath}` — Path to implementation plan
- `{ReviewerName}` — Human reviewer
- `{SignOffDate}` — ISO date

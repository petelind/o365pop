# Implementation Plan Template

**Type**: Document
**Required**: No
**Produced by**: Plan Feature

# Implementation Plan Template

**Artifact ID**: 9
**Type**: Template
**Required**: True

## Description

# {FeatureName} - Implementation Plan

**Feature**: {FeatureScreenID} {FeatureTitle}
**Feature File**: `{FeatureFilePath}`
**GitHub Issues**: {IssueNumbers} ({ScenarioIDs})
**Branch**: `feature/{feature-slug}`

---

## Context Map

*3-5 file:line_range references for cold-start orientation. Read these first before touching any code.*

| File | Lines | Why |
|---|---|---|
| `{FilePath1}` | {N}-{M} | {Why this area matters} |
| `{FilePath2}` | {N}-{M} | {Why this area matters} |
| `{FilePath3}` | {N}-{M} | {Why this area matters} |

## Do Not Do

*Explicit out-of-scope guardrails. Violating these is a footprint_violation.*

- Do not touch {OutOfScopeArea1} — {Reason1}
- Do not add {OutOfScopeChange2} — {Reason2}
- Do not modify {OutOfScopeArea3} — {Reason3}

## SAO.md Sections That Apply

*Read these SAO.md sections before implementing. Check compliance before every checkpoint.*

- {SectionHeading1} (e.g., "3.2 Service Layer")
- {SectionHeading2} (e.g., "4.1 MCP Tool Contracts")
- {SectionHeading3}

## Log Story Script (Mandatory Section E)

*Each row is a beat the implementor must emit at INFO and prove with pytest caplog. Never defer logging to a final slice.*

```
## Log Story Script
| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `{Class.method}` | entry | method called | {key=} |
| `{Class.method}` | branch | {reject_condition} | {reason=} |
| `{Class.method}` | exit | success/fail | status= / id= |
```

Beats: `entry | config | validation | processing | branch | exit | error`.

### Tests to Create — log story rows (Mandatory Section D addendum)

| Test | Level | Proves |
|------|-------|--------|
| `test_{feature}_log_story_happy` | view/integration | Log Story Script happy-path beats via caplog |
| `test_{feature}_log_story_reject` | view/integration | Log Story Script reject-path beats via caplog |

### Tests to Create — agent proof rows (Mandatory Section D addendum, when Section G populated)

| Test | Level | Proves |
|------|-------|--------|
| `test_{feature}_agent_story_happy` | integration (`@agent_proof`) | Agent Proof Table happy-path trace beats via `assert_agent_story` |
| `test_{feature}_agent_story_reject` | integration (`@agent_proof`) | Agent Proof Table reject-path trace beats (adverse PRF rows) |

### Dual checkpoint (when used under PIN)

```yaml
checkpoint:
  command: "pytest ...::{behavior_test} -x"
  log_story_command: "pytest ...::{log_story_test} -x"
  agent_proof_command: "pytest ...::{agent_story_test} -m agent_proof -x"  # when Section G populated
```

DoD: every **declared** command passes — behavior always; `log_story_command` when Section E has rows; `agent_proof_command` when Section G has rows. Omit undeclared keys.

---

## Agent Proof Table (Mandatory Section G)

*Skip with "Not applicable" if SAO §17 is N/A or this feature does not touch agent capabilities.*

```
## Agent Proof Table
| PRF ID | Workflow | Script path | Trace beats to assert | Adverse? |
|--------|----------|-------------|----------------------|----------|
| PRF-SC01-04 | munin_chat | tests/fixtures/llm_scripts/PRF-SC01-04/happy.json | tools_blocked: list_entities | yes |
| PRF-SC01-04 | munin_chat | tests/fixtures/llm_scripts/PRF-SC01-04/reject_blocked.json | tools_blocked: list_entities | yes |
```

Rules:
- Map only PRF rows from SAO §17 / DTA-19 §13 that this feature affects.
- Script paths under `tests/fixtures/llm_scripts/<prf-id>/` (`happy.json`, `reject_*.json`).
- Section D must name matching `test_*_agent_story_*` tests for every selected PRF row.
- Trace beats use artifact 56 Part 4.5 addendum vocabulary: **workflow**, **tools**, **domain**, **board/plan**.
- TASK-* golden tasks (lane 4) belong in SAO §17 / nightly eval — list in plan only when this slice introduces or changes a golden task fixture.
- Reference: artifact 56 Part 4.5, skill *Agent Integration Proof Patterns*, rule `do-assert-agent-story`.

---

## Current State Assessment

### What Exists (Reusable)

1. **{ComponentName1}** - `{FilePath1}`
   - {ExistingFunctionality1}
   - {ExistingFunctionality2}
   - **Decision**: {ReuseDecision1}

2. **{ComponentName2}** - `{FilePath2}`
   - {ExistingFunctionality3}
   - {ExistingFunctionality4}
   - **Decision**: {ReuseDecision2}

3. **{ComponentName3}** - `{FilePath3}`
   - {ExistingFunctionality5}
   - **Decision**: {ReuseDecision3}

### What's Missing

1. **{MissingComponent1}** - {ScenarioID1}
2. **{MissingComponent2}** - {ScenarioID2}
3. **{MissingComponent3}** - {ScenarioID3}
4. **{MissingComponent4}** - {ScenarioID4}
5. **{MissingComponent5}** - {ScenarioID5}

### Issues to Fix

1. **{Issue1}**: {IssueDescription1}
2. **{Issue2}**: {IssueDescription2}
3. **{Issue3}**: {IssueDescription3}

---

## Clarification Questions

### Q1: {QuestionTopic1}
**Question**: {QuestionText1}
**Answer**: {AnswerText1}

### Q2: {QuestionTopic2}
**Question**: {QuestionText2}
**Answer**: {AnswerText2}

### Q3: {QuestionTopic3}
**Question**: {QuestionText3}
**Answer**: {AnswerText3}

---

## Implementation Plan

### Phase 0: Preparation

- [ ] **0.1** Create feature branch
  ```bash
  git checkout -b feature/{feature-slug}
  ```

- [ ] **0.2** Read workflow files
  - Read BPE-02 / BPE-03 activity guidance
  - Read skill *Pytest Log Story Assertions* when Section E is populated

---

### Phase 1: {Phase1Title} ({ScenarioID1}, {ScenarioID2})

**Scenario**: {ScenarioDescription}
**GitHub Issue**: {IssueNumber}

#### Backend Changes

- [ ] **1.1** {BackendTask1}
  - **File**: `{FilePath}`
  - **Change**: {ChangeDescription}
  - **Test**: `{TestFilePath}`

- [ ] **1.2** {BackendTask2}
  - **File**: `{FilePath}`
  - **Models**: {ModelChanges}
  - **Test**: `{TestFilePath}`

- [ ] **1.3** {BackendTask3}
  - **File**: `{FilePath}`
  - **Services**: {ServiceChanges}
  - **Test**: `{TestFilePath}`

- [ ] **1.4** {BackendTask4}
  - **File**: `{FilePath}`
  - **Views**: {ViewChanges}
  - **Test**: `{TestFilePath}`

- [ ] **1.5** {BackendTask5}
  - **File**: `{FilePath}`
  - **URLs**: {URLChanges}
  - **Test**: `{TestFilePath}`

#### Frontend Changes

- [ ] **1.6** {FrontendTask1}
  - **File**: `{TemplatePath}`
  - **Template**: {TemplateChanges}
  - **Test**: `{TestFilePath}`

- [ ] **1.7** {FrontendTask2}
  - **File**: `{TemplatePath}`
  - **HTMX**: {HTMXChanges}
  - **Test**: `{TestFilePath}`

- [ ] **1.8** {FrontendTask3}
  - **File**: `{TemplatePath}`
  - **Semantic Attributes**: {SemanticAttributes}
  - **Test**: `{TestFilePath}`

#### Testing

- [ ] **1.9** Unit tests for {Component}
  - **File**: `tests/unit/test_{component}.py`
  - **Tests**: {UnitTestList}

- [ ] **1.10** Integration tests for {Scenario}
  - **File**: `tests/integration/test_{feature}_{scenario}.py`
  - **Tests**: {IntegrationTestList}

- [ ] **1.11** View tests for {View}
  - **File**: `tests/integration/test_{view}_views.py`
  - **Tests**: {ViewTestList}

- [ ] **1.12** Log story tests (caplog)
  - **File**: same as view/integration test module
  - **Tests**: `test_{feature}_log_story_happy`, `test_{feature}_log_story_reject`
  - **Helper**: `tests/support/log_story.py` → `assert_log_story`

#### Commit

- [ ] **1.13** Commit Phase 1 (behavior + log story green)
  ```bash
  git add .
  git commit -m "feat({scope}): {commit-message}

  {commit-body}

  Implements: {ScenarioID1}, {ScenarioID2}
  Closes: {IssueNumber}"
  ```

---

### Phase 2: {Phase2Title} ({ScenarioID3}, {ScenarioID4})

**Scenario**: {ScenarioDescription}
**GitHub Issue**: {IssueNumber}

#### Backend Changes

- [ ] **2.1** {BackendTask1}
  - **File**: `{FilePath}`
  - **Change**: {ChangeDescription}

- [ ] **2.2** {BackendTask2}
  - **File**: `{FilePath}`
  - **Change**: {ChangeDescription}

#### Frontend Changes

- [ ] **2.3** {FrontendTask1}
  - **File**: `{TemplatePath}`
  - **Change**: {ChangeDescription}

- [ ] **2.4** {FrontendTask2}
  - **File**: `{TemplatePath}`
  - **Change**: {ChangeDescription}

#### Testing

- [ ] **2.5** Unit tests
  - **File**: `{TestFilePath}`
  - **Tests**: {TestList}

- [ ] **2.6** Integration tests
  - **File**: `{TestFilePath}`
  - **Tests**: {TestList}

#### Commit

- [ ] **2.7** Commit Phase 2
  ```bash
  git commit -m "feat({scope}): {commit-message}"
  ```

---

### Phase 3: {Phase3Title} ({ScenarioID5})

**Scenario**: {ScenarioDescription}
**GitHub Issue**: {IssueNumber}

#### Backend Changes

- [ ] **3.1** {BackendTask}
  - **File**: `{FilePath}`
  - **Change**: {ChangeDescription}

#### Frontend Changes

- [ ] **3.2** {FrontendTask}
  - **File**: `{TemplatePath}`
  - **Change**: {ChangeDescription}

#### Testing

- [ ] **3.3** Integration tests
  - **File**: `{TestFilePath}`
  - **Tests**: {TestList}

#### Commit

- [ ] **3.4** Commit Phase 3
  ```bash
  git commit -m "feat({scope}): {commit-message}"
  ```

---

### Phase 4: E2E Testing & Finalization

#### E2E Tests (Playwright)

- [ ] **4.1** Create E2E test file
  - **File**: `tests/e2e/test_{feature}_journey.py`
  - **Tests**: Complete user journey from {StartPoint} to {EndPoint}

- [ ] **4.2** Implement E2E scenarios
  - {E2EScenario1}
  - {E2EScenario2}
  - {E2EScenario3}

#### Documentation

- [ ] **4.3** Update README if needed
  - Document new feature
  - Update setup instructions

- [ ] **4.4** Update feature file with completion markers
  - Mark implemented scenarios
  - Add implementation notes

#### Final Checks

- [ ] **4.5** Run full test suite
  ```bash
  pytest tests/
  ```

- [ ] **4.6** Run linter
  ```bash
  make lint
  ```

- [ ] **4.7** Check test coverage
  ```bash
  pytest --cov={app} tests/
  ```

- [ ] **4.8** Manual smoke test
  - Test all scenarios in browser
  - Verify UI/UX matches mockups

#### Commit & PR

- [ ] **4.9** Final commit
  ```bash
  git commit -m "test({scope}): add E2E tests for {feature}"
  ```

- [ ] **4.10** Push branch
  ```bash
  git push origin feature/{feature-slug}
  ```

- [ ] **4.11** Create Pull Request
  - **Title**: `{FeatureName} - {ScenarioIDs}`
  - **Description**: Link to feature file, implementation plan, and issues
  - **Reviewers**: {ReviewerNames}

---

## Definition of Done Checklist

- [ ] All scenarios from feature file implemented
- [ ] Unit tests: 100% pass rate
- [ ] Integration tests: 100% pass rate
- [ ] E2E tests: 100% pass rate
- [ ] Log Story Script rows proven by caplog (`*_log_story_*` or `log_story_command`)
- [ ] Agent Proof Table rows proven by `@agent_proof` tests (`*_agent_story_*` or `agent_proof_command`) when Section G populated
- [ ] No deferred agent-proof slice
- [ ] No deferred logging slice
- [ ] Code coverage: {CoverageTarget}% minimum
- [ ] Linter: 0 errors, 0 warnings
- [ ] All `data-testid` attributes added for Playwright
- [ ] All forms have proper validation
- [ ] All error messages are user-friendly
- [ ] All success messages are clear
- [ ] Responsive design verified (mobile, tablet, desktop)
- [ ] Accessibility: ARIA labels, keyboard navigation
- [ ] Documentation updated
- [ ] Feature file marked complete
- [ ] GitHub issues closed
- [ ] PR approved and merged

---

## Notes

### Architecture Decisions
- {ArchitectureDecision1}
- {ArchitectureDecision2}

### Technical Debt
- {TechnicalDebt1}
- {TechnicalDebt2}

### Future Enhancements
- {FutureEnhancement1}
- {FutureEnhancement2}

---

## Placeholder Reference

- `{FeatureName}` - Feature name (e.g., "Authentication", "Playbook Management")
- `{FeatureScreenID}` - Screen ID (e.g., FOB-AUTH-LOGIN-1)
- `{ScenarioID}` - Scenario ID (e.g., AUTH-01, PLAYBOOKS-LIST-01)
- `{FilePath}` - File path relative to project root
- `{ComponentName}` - Component/module name
- `{ModelChanges}` - Model changes description
- `{ServiceChanges}` - Service changes description
- `{ViewChanges}` - View changes description
- `{URLChanges}` - URL routing changes
- `{TemplateChanges}` - Template changes description
- `{HTMXChanges}` - HTMX interaction changes
- `{TestFilePath}` - Test file path
- `{TestList}` - List of tests to implement
- `{IssueNumber}` - GitHub issue number
- `{feature-slug}` - Feature slug for branch name (lowercase, hyphenated)
- `{scope}` - Commit scope (e.g., auth, playbooks, workflows)
- `{commit-message}` - Commit message following Angular convention

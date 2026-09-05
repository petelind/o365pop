# GitHub Issue Operations

**Capability**: GITHUB_ISSUE  
**Stack**: GitHub CLI

# Skill: GitHub Issue Operations

**Capability Domain**: GITHUB_ISSUE  
**Technology Stack**: GitHub CLI

## Overview

Patterns for creating, reading, updating, and commenting on GitHub Issues as ScenarioExecution records. Covers the `<!-- SCENARIO -->` YAML embedding convention, label management for iteration state, and structured comment templates for checkpoints and drift signals.

## Reference Implementation

### Pattern 1: Create Scenario Issue with SCENARIO Block

```bash
gh issue create \
  --title "[S1][A] User can export workflow as JSON" \
  --label "status-queued,parallel-group-A,medium" \
  --milestone "{milestone_number}" \
  --body "$(cat <<'EOF'
<!-- SCENARIO -->
id: S1
parallel_group: A
skeleton_commit: "abc1234"
codebase_footprint:
  - mcp_integration/tools.py
  - methodology/services/workflow_export_service.py
  - tests/integration/test_mcp_export.py
checkpoint:
  command: "pytest tests/integration/test_mcp_export.py -x"
  expected_exit_code: 0
dependencies: []
sao_sections:
  - "§Services Layer"
  - "§MCP Access Rules"
do_not_do:
  - "Do NOT create a new Django app"
  - "Do NOT add a manager layer between view and service"
  - "Do NOT modify existing service method signatures"
rollback_point: "git stash"
<!-- /SCENARIO -->

## Context Map
| File | Lines | Note |
|------|-------|------|
| methodology/services/workflow_service.py | 45–80 | Follow this exact pattern |
| mcp_integration/tools.py | 120–145 | Append here, do NOT restructure |
| tests/integration/test_workflow_crud.py | 1–40 | Follow fixture setup pattern |

## Do Not Do
- Do NOT create a new Django app
- Do NOT add a manager layer between view and service
- Do NOT modify existing service method signatures

## SAO.md Sections That Apply
- §Services Layer: shared by MCP and Web UI, no MCP-specific logic in services
- §MCP Access Rules: draft = full CRUD, released = read-only

## Implementation Plan
{BPE-01 implementation plan content — full text, not a link}

## Acceptance Criteria
- [ ] `pytest tests/integration/test_mcp_export.py -x` passes (exit code 0)
- [ ] No regressions: `pytest tests/ -x --ignore=tests/e2e` passes
- [ ] Changes committed with Angular convention message
EOF
)"
```

### Pattern 2: Parse SCENARIO YAML from Issue Body

```bash
# Get issue body
ISSUE_BODY=$(gh issue view {issue_number} --json body --jq '.body')

# Extract and parse SCENARIO block
python3 - <<EOF
import re, yaml

body = """$ISSUE_BODY"""
match = re.search(r'<!-- SCENARIO -->(.+?)<!-- /SCENARIO -->', body, re.DOTALL)
if match:
    scenario = yaml.safe_load(match.group(1))
    print('ID:', scenario['id'])
    print('Group:', scenario['parallel_group'])
    print('Skeleton commit:', scenario['skeleton_commit'])
    print('Checkpoint:', scenario['checkpoint']['command'])
    print('Footprint:', scenario['codebase_footprint'])
    print('SAO sections:', scenario['sao_sections'])
    print('Do not do:', scenario['do_not_do'])
    print('Dependencies:', scenario['dependencies'])
EOF
```

### Pattern 3: Transition Issue Labels (state machine)

```bash
# queued -> in-progress
gh issue edit {issue_number} \
  --add-label "status-in-progress" \
  --remove-label "status-queued"

# in-progress -> done (also closes)
gh issue close {issue_number}
gh issue edit {issue_number} \
  --add-label "status-done" \
  --remove-label "status-in-progress"

# in-progress -> escalated (drift)
gh issue edit {issue_number} \
  --add-label "drift-escalated" \
  --remove-label "status-in-progress"
```

### Pattern 4: Checkpoint Pass Comment

```bash
gh issue comment {issue_number} --body "<!-- CHECKPOINT_PASS -->
Checkpoint passed at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Command: {command}
<!-- /CHECKPOINT_PASS -->"
```

### Pattern 5: Absorbed Drift Comment

```bash
gh issue comment {issue_number} --body "<!-- DRIFT absorbed -->
type: checkpoint_fail
detected_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
action: {description of targeted fix applied}
retry: PASS
<!-- /DRIFT -->"
gh issue edit {issue_number} --add-label "drift-absorbed"
```

### Pattern 6: Escalate Comment

```bash
gh issue comment {issue_number} --body "<!-- ESCALATE -->
type: {footprint_violation|method_explosion|sao_violation|checkpoint_fail_retry}
evidence: {specific — file name / method name / SAO constraint / test output}
jedao_recommendation: {A: fix and retry | B: resequence | C: scope reduce}
await_human_decision: true
<!-- /ESCALATE -->"
gh issue edit {issue_number} \
  --add-label "drift-escalated" \
  --remove-label "status-in-progress"
```

### Pattern 7: Get Next Eligible Scenario

```bash
# Get all queued issues for milestone
gh issue list \
  --milestone {N} \
  --label "status-queued" \
  --json number,title,labels,body \
  --jq '.[] | {number, title, labels: [.labels[].name]}'

# Filter for scenarios with all dependencies met
python3 - <<EOF
import subprocess, json, re, yaml

issues = json.loads(subprocess.check_output([
    'gh', 'issue', 'list', '--milestone', '{N}',
    '--label', 'status-queued', '--json', 'number,title,body'
]))

for issue in issues:
    body = issue['body']
    match = re.search(r'<!-- SCENARIO -->(.+?)<!-- /SCENARIO -->', body, re.DOTALL)
    if not match:
        continue
    scenario = yaml.safe_load(match.group(1))
    deps = scenario.get('dependencies', [])
    # For each dep scenario ID, verify its github_issue is closed with status-done
    # (look up from manifest or iterate closed issues)
    all_done = all(
        'status-done' in subprocess.check_output(
            ['gh', 'issue', 'view', str(dep_issue), '--json', 'labels', '--jq', '[.labels[].name]']
        ).decode()
        for dep_issue in deps  # dep_issue numbers from manifest
    ) if deps else True
    if all_done:
        print(f"ELIGIBLE: #{issue['number']} {issue['title']}")
        break
EOF
```

## Required Labels

```bash
for label in \
  "status-queued:#e4e669" \
  "status-in-progress:#0075ca" \
  "status-done:#0e8a16" \
  "drift-absorbed:#fef2c0" \
  "drift-escalated:#e11d48" \
  "parallel-group-A:#bfd4f2" \
  "parallel-group-B:#d4c5f9" \
  "parallel-group-C:#f9d0c4" \
  "backlog:#ededed"; do
  name=$(echo $label | cut -d: -f1)
  color=$(echo $label | cut -d: -f2)
  gh label create "$name" --color "$color" 2>/dev/null || true
done
```

## Quality Gates

- [ ] Every scenario issue has `<!-- SCENARIO -->` block parseable as YAML
- [ ] `skeleton_commit` field present and is a valid git hash
- [ ] `sao_sections[]` and `do_not_do[]` fields present and non-empty
- [ ] Context Map, Do Not Do, SAO Sections, and Implementation Plan all present inline (not linked)
- [ ] Every scenario issue linked to correct milestone
- [ ] Labels transition correctly through state machine
- [ ] Drift comments include `type`, `detected_at`, `evidence`
- [ ] Escalate comments include `jedao_recommendation` and specific `evidence`

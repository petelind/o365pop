# Iteration Lessons Learned Document

**Type**: Document
**Required**: Yes
**Produced by**: TL Closes Sprint with Lessons and Release

A structured Markdown document recording the retrospective of a completed iteration. Produced by the Team Lead (AI orchestrator) during the sprint close activity that supersedes Activity 182 (Close Iteration) in Workflow 17.

Authored using Skill 28 (Lessons Learned Writing). Skill 28 should be linked to the producing close activity.

Location: `docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md`

Front-matter fields: iteration slug, milestone number + goal, scenarios_planned, scenarios_delivered, fix_cycles, uat_blockers_found, uat_blockers_resolved, test_debt_found.

Sections:
- Execution Review (per-scenario deviations and drift signals during Execute, Activity 181)
- Acceptance Testing (Saga scope, blocker count, fix cycle count)
- Test Debt (stale test assertions filed, coverage gaps identified)
- Architecture Notes (SAO.md updates applied or deferred as sao-update issues)

Lifecycle: created during close activity, committed to `docs/lessons_learned/`, then read-only.

Consumed by: Orient & Validate Scope (Activity 140 in Plan Iteration workflow) as velocity and scope-risk context for the next iteration.

# Execution Manifest

**Type**: Document  
**Required**: Yes  
**Produced by**: Contract

# Execution Manifest (ITER-*.yaml)

The machine-readable iteration contract produced by PIT-02 Contract. Embedded inside the GitHub Milestone description as a `<!-- MANIFEST --> ... <!-- /MANIFEST -->` YAML block. MIT reads this block at activation time to load all execution parameters without requiring codebase exploration.

## Purpose

Provides MIT (Manage Iteration) with everything needed to execute the iteration cold-start:
- Which scenarios to run and in what order
- The skeleton commit hash to diff against for footprint checking
- The SAO.md sections that constrain each scenario
- The context map (3–5 file:line_range references) for cold-start orientation
- The do-not-do guardrails that define footprint boundaries
- The checkpoint command to verify each scenario is done

## Schema

```yaml
iteration:
  goal: string                    # "Verb noun so that success signal"
  doctrine_version: string        # "2.0"
  created_at: ISO8601

conflict_map:
  {filename}: [S1, S2]            # files shared between scenarios; from skeleton commit diffs

parallel_groups:
  A: [S1]
  B: [S3]
  C: [S2]

scenarios:
  S{N}:
    title: string
    github_issue: int              # null until PIT-03 Publish runs
    parallel_group: string
    skeleton_commit: string        # commit hash from PIT-02 skeleton; null until then
    sao_sections: [string]         # SAO.md headings that constrain this scenario
    context_map: [string]          # 3-5 "file:line_range" references for cold-start
    do_not_do: [string]            # explicit out-of-scope guardrails
    codebase_footprint: [string]   # file paths MIT is allowed to touch
    checkpoint:
      command: string
      expected_exit_code: int
    dependencies: [string]
    rollback_point: string
```

## Lifecycle

1. **Created**: PIT-02 Contract — initial skeleton with `skeleton_commit: null`, `github_issue: null`
2. **skeleton_commit filled**: After PIT-02 skeleton commit is pushed
3. **github_issue filled**: After PIT-03 Publish creates GitHub issues
4. **Read**: MIT-01 Activate Iteration loads this block; MIT-02 Execute Loop reads per-scenario fields
5. **Updated**: MIT-03 Handle Drift may patch scenario fields after human decision (scope reduce)
6. **Archived**: MIT-04 Close Iteration records final manifest state in lessons learned file

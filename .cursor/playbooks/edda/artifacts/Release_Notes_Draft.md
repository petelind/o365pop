# Release Notes Draft

**Type**: Document
**Required**: Yes
**Produced by**: TL Closes Sprint with Lessons and Release

A single artifact with two lifecycle stages, both produced during the sprint close activity that supersedes Activity 182 (Close Iteration) in Workflow 17.

**Stage 1 — Draft (internal):** Assembled by the Team Lead (AI orchestrator) and presented to the human at the release gate. Content: iteration slug + goal, list of delivered scenarios with linked GitHub issues, acceptance verdict (CLEAN) with blocker resolution count, test health summary (CRITICALs resolved, WARNINGs deferred), and deferred non-blocker issues. Produced with Skill 32 (GitHub Issue Operations).

**Stage 2 — Published:** The approved draft becomes the body of `gh release create --target {merge_sha}`. The resulting GitHub Release is the artifact's published form, discoverable via the repository's Releases page.

Transition: the draft advances to published only on explicit human approval ("release" keyword at the human gate in the close activity).

Consumed by: stakeholders and next-iteration scope review (Orient & Validate Scope, Activity 140).

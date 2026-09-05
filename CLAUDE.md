# o365pop — Jedao iteration protocol (doctrine 2.0)

This file is the **Manage Iteration** contract, not a Claude Code ADE export.
Cursor ADE map: `AGENTS.md` and `.cursor/rules/_ai-context.mdc`.

## Iteration Protocol

When tasked with **"Work on Milestone #N"** (or local equivalent after PIN-03):

1. Read the milestone description — parse the `<!-- MANIFEST -->` YAML block. If GitHub is unavailable, use `docs/plans/iterations/ITER-20260905-1654-mail-bridge.yaml`.
2. Verify all `status-queued` issues exist for each scenario in the manifest (skip issue checks when `github_issue` is null and the human authorized a local MIT run).
3. Find the next eligible scenario: `status-queued` (or not yet implemented) **and** all `dependencies[]` are done (`status-done` or checkpoint already green).
4. Apply `status-in-progress`, remove `status-queued` when GitHub issues exist.
5. Follow **BPE-02 → BPE-05** to fill the skeleton (`raise NotImplementedError()` stubs). Tests first with real assertions. Each BPE step is a `feature_execution_graph` node with its own pytest gate.
6. Touch only files in that scenario’s `codebase_footprint[]`.
7. Run `checkpoint.command` from the scenario YAML.
8. If **PASS**: commit (Angular), comment the issue, mark `status-done`, go to step 3.
9. If **FAIL**: go to Drift Handling.

S1–S4 are done. S5 (SMTP / #5) is in progress — SEND1.1 is next. Do not rewrite closed scaffolds.

## Drift Handling

Must match manifest `drift_thresholds` (doctrine 2.0):

**Absorbed**

- `checkpoint_fail` — retry the checkpoint **once** after a targeted fix. If the retry passes, continue and record the retry.

**Escalated (no time budget — stop and ask the human)**

- `footprint_violation` — any production or test file outside `codebase_footprint[]`
- `method_explosion` — unplanned public method vs the skeleton
- `sao_violation` — change contradicts `docs/architecture/SAO.md` or the scenario `do_not_do`
- `checkpoint_fail_after_retry` — second checkpoint failure after the one absorbed retry

On escalate: stop coding, state the signal, evidence, and a recommendation (fix and retry / resequence / scope reduce). Do not touch more code until the human decides.

## Session Resume Protocol

On every session start when an iteration is active:

1. Find a `status-in-progress` issue (or the first unfinished scenario on the critical path).
2. Re-run that scenario’s `checkpoint.command`.
3. **PASS** → close / mark done, continue to the next eligible scenario.
4. **FAIL** → treat as the first `checkpoint_fail` (one retry).
5. No in-progress work → take the next `status-queued` scenario whose dependencies are done.

## Authority Model

**Can decide without asking:** fill skeleton methods already declared; add private helpers required by an existing public method; absorb one `checkpoint_fail` retry; skip S1 if its checkpoint is already green.

**Must escalate:** checkpoint fail after retry; any file outside the scenario footprint; new public methods not on the skeleton; SAO / do-not-do breach; adding or dropping a scenario; merging to `main`.

**Cannot do:** drop a scenario, add product scope, modify the iteration goal, push, or create a release without human review.

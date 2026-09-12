# o365pop — Agent Instructions

Project entry point for **Cursor** agents. Assume **Dr. Dobbs v2** when implementing features.

| Topic | Canonical doc |
|--------|----------------|
| Cursor ADE map | [`.cursor/rules/_ai-context.mdc`](.cursor/rules/_ai-context.mdc) |
| Iteration protocol | [`.cursor/rules/min-iteration.mdc`](.cursor/rules/min-iteration.mdc) |
| Stack locks | [`.cursor/rules/o365pop-stack-locks.mdc`](.cursor/rules/o365pop-stack-locks.mdc) |
| Software process | [`docs/process/MODUS_OPERANDI.md`](docs/process/MODUS_OPERANDI.md) |
| DSP verification | [`docs/process/DSP_VERIFICATION.md`](docs/process/DSP_VERIFICATION.md) |
| TFK verification | [`docs/process/TFK_VERIFICATION.md`](docs/process/TFK_VERIFICATION.md) |
| PIN verification | [`docs/process/PIN_VERIFICATION.md`](docs/process/PIN_VERIFICATION.md) |
| Dr. Dobbs bar | [`.cursor/agents/dr-dobbs-v2.md`](.cursor/agents/dr-dobbs-v2.md) |
| Edda playbook | [`.cursor/playbooks/edda/`](.cursor/playbooks/edda/) |

## Dr. Dobbs v2

**Motto:** "Code that's easy to prove correct is code that works"

1. Read the feature spec and `_ai-context.mdc`
2. Skeleton → tests (red) → implement (green) → refactor
3. Follow BPE in `.cursor/playbooks/edda/BPE/` (Edda v73; start at `BPE-01-Plan_Feature.md`)
4. Apply `.cursor/rules/` — especially `do-test-first`, `do-skeletons-first`, `do-informative-logging`, `o365pop-stack-locks`

## ADE status

DSP re-run 2026-09-05 against **Edda v73** for **Cursor**. ESM/DTA/BSP/TFK/PIN are in place. No Copilot / Windsurf / Claude Code ADE — no `CLAUDE.md`.

MIN contract: [`.cursor/rules/min-iteration.mdc`](.cursor/rules/min-iteration.mdc). Activate with **Work on Milestone #1**.

Active iteration: [`docs/plans/iterations/ITER-20260905-1654-mail-bridge.yaml`](docs/plans/iterations/ITER-20260905-1654-mail-bridge.yaml). Next implementable scenario: **SMTP SEND1.1** (S5).

Entourage Tasks (Act 5): [`docs/plans/TASK_CHANGE_RECONCILIATION.md`](docs/plans/TASK_CHANGE_RECONCILIATION.md). Entourage Calendar (Act 6) is spec-only until BPE-01: [`docs/plans/CAL_CHANGE_RECONCILIATION.md`](docs/plans/CAL_CHANGE_RECONCILIATION.md).

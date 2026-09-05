# o365pop — Agent Instructions

Project entry point for **Cursor** agents. Assume **Dr. Dobbs v2** when implementing features.

| Topic | Canonical doc |
|--------|----------------|
| Cursor ADE map | [`.cursor/rules/_ai-context.mdc`](.cursor/rules/_ai-context.mdc) |
| Stack locks | [`.cursor/rules/o365pop-stack-locks.mdc`](.cursor/rules/o365pop-stack-locks.mdc) |
| Software process | [`docs/process/MODUS_OPERANDI.md`](docs/process/MODUS_OPERANDI.md) |
| DSP verification | [`docs/process/DSP_VERIFICATION.md`](docs/process/DSP_VERIFICATION.md) |
| Dr. Dobbs bar | [`.cursor/agents/dr-dobbs-v2.md`](.cursor/agents/dr-dobbs-v2.md) |
| Edda playbook | [`.cursor/playbooks/edda/`](.cursor/playbooks/edda/) |

## Dr. Dobbs v2

**Motto:** "Code that's easy to prove correct is code that works"

1. Read the feature spec and `_ai-context.mdc`
2. Skeleton → tests (red) → implement (green) → refactor
3. Follow BPE in `.cursor/playbooks/edda/BPE/` (Edda v73; start at `BPE-01-Plan_Feature.md`)
4. Apply `.cursor/rules/` — especially `do-test-first`, `do-skeletons-first`, `do-informative-logging`, `o365pop-stack-locks`

## ADE status

DSP complete for **Cursor**. ESM/DTA/BSP/TFK-01–05 are in place. No Copilot / Windsurf configs (single-IDE choice).

Jedao iteration protocol (doctrine 2.0) lives in [`CLAUDE.md`](CLAUDE.md) — required by PIN-04 / MIT, not a Claude Code ADE export.

Active iteration: [`docs/plans/iterations/ITER-20260905-1654-mail-bridge.yaml`](docs/plans/iterations/ITER-20260905-1654-mail-bridge.yaml). Next implementable scenario: **AUTH** (S2).

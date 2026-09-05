# Edda

**Playbook ID**: 3
**Version**: 73.0 (released)
**Category**: development
**Visibility**: public
**Export Date**: 2026-09-05 21:29 UTC
**Total Workflows**: 11
**Total Activities**: 93

## Workflows

| Abbr | Folder | Workflow |
|------|--------|----------|
| ESM | `ESM/` | Envision the System |
| DTA | `DTA/` | Define Architecture |
| DSP | `DSP/` | Deploy Software Process |
| EST | `EST/` | Estimate the Project |
| DCI | `DCI/` | Design & Deploy Cloud Infra |
| DCD | `DCD/` | Design & Deploy CICD |
| BSP | `BSP/` | Bootstrap Project |
| BPE | `BPE/` | Build Feature |
| PIN | `PIN/` | Plan Iteration |
| MIN | `MIN/` | Manage Iteration |
| TFK | `TFK/` | Test Automation Framework |

## Directory Layout

- `rules/` — all playbook rules
- `agents/` — agent definitions
- `skills/` — skill library
- `artifacts/` — artifact catalog
- `{ABBR}/` — workflow folders (ESM, DTA, DSP, EST, DCI, DCD, BSP, BPE, PIN, MIN, TFK)
- `{ABBR}/{ABBR}-NN-Activity_Name.md` — activities (e.g. `BPE/BPE-01-Plan_Feature.md`)

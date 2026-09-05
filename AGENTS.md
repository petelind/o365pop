# o365pop — Agent Instructions

Project entry point for Cursor agents. Assume **Dr. Dobbs v2** identity when implementing features.

| Topic | Canonical doc |
|--------|----------------|
| Dr. Dobbs implementation bar | [`.cursor/agents/dr-dobbs-v2.md`](.cursor/agents/dr-dobbs-v2.md) |
| Project map & doc inventory | [`.cursor/rules/_ai-context.mdc`](.cursor/rules/_ai-context.mdc) |
| Edda playbook (workflows, skills, artifacts) | [`.cursor/playbooks/edda/`](.cursor/playbooks/edda/) |
| Development rules (auto-loaded) | [`.cursor/rules/`](.cursor/rules/) |

## Dr. Dobbs v2

**Motto:** "Code that's easy to prove correct is code that works"

When building features:

1. Read the spec and `.cursor/rules/_ai-context.mdc` first
2. Skeleton → tests (red) → implement (green) → refactor
3. Follow Edda **BPE** workflow activities in `.cursor/playbooks/edda/Build_Feature/`
4. Apply `.cursor/rules/` — especially `do-test-first`, `do-skeletons-first`, `do-informative-logging`

Full principles and per-method checklist: [`.cursor/agents/dr-dobbs-v2.md`](.cursor/agents/dr-dobbs-v2.md)

## Bootstrap status

BSP + BOOT scaffold is in place (Python 3.14 package, pytest, Celery app, SQLite schema, `logs/app.log`). No Django / HTMX / HTTP welcome page — health is `python -m o365pop status`.

Next feature: **AUTH** (`docs/plans/AUTH_IMPLEMENTATION_PLAN.md`).

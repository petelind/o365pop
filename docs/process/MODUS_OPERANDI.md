# Modus operandi

How humans and Cursor agents build o365pop. Architecture lock: `docs/architecture/SAO.md`. ADE lock: `.cursor/rules/_ai-context.mdc`.

## Target ADE

**Cursor.** Rules in `.cursor/rules/*.mdc` (`alwaysApply`). Agent bar: Dr. Dobbs v2 (`.cursor/agents/dr-dobbs-v2.md`). Playbook: `.cursor/playbooks/edda/`.

Do not generate Windsurf, Claude Code, or Copilot configs unless DSP-04 is re-run.

## Delivery loop

1. **Plan** — BPE-01 against the feature file + SAO. One feature at a time (`docs/plans/O365POP_IMPLEMENTATION_PLAN.md`).
2. **Slice** — skeleton → red pytest → green → refactor (`do-skeletons-first`, `do-test-first`).
3. **Observe** — log beats in the same commit (`do-informative-logging`, `assert_log_story`).
4. **Prove** — feature checkpoint command from the plan; `make test` is the merge gate (`not live_graph`).
5. **Commit** — Angular conventional commits. Do not push unless asked.
6. **Catalog** — TFK-07: add phrase/fixture rows when a new scenario lands.

## Stack locks (do not violate)

- No Django, FastAPI, HTMX, Playwright, Graph SDK
- `popd` / `smtpd` must not import `o365pop.graph`
- No TLS on POP/SMTP; do not bind 110/587 on the WAN NIC
- Never log tokens, mailbox passwords, or raw MIME bodies
- Integration: no `unittest.mock` on domain services

## Where to look

| Need | Open |
|---|---|
| What to build | `docs/features/act-1-bridge/*.feature` |
| How it is proven | `docs/features/CATALOG.md`, `tests/fixtures/CATALOG.md` |
| How to implement | matching `docs/plans/*_IMPLEMENTATION_PLAN.md` |
| How to run | `make help` |

Next feature after BOOT+TFK+DSP: **AUTH**.

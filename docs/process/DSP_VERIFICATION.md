# DSP verification — Cursor ADE (Edda v73 re-run)

**Workflow:** Deploy Software Process (DSP-01 → DSP-06)
**Playbook:** Edda v73.0 (`.cursor/playbooks/edda/`)
**Target IDE:** Cursor (DSP-04; operator lock — no Windsurf / Copilot / Claude Code ADE)
**Date:** 2026-09-05

DSP-04 target is **Cursor**. ADE is `.cursor/rules/_ai-context.mdc` plus other `.cursor/rules/*.mdc`. There is no `CLAUDE.md` (that file is Claude Code only). MIN protocol: `.cursor/rules/min-iteration.mdc`.

---

## DSP-01 ESM artifacts

```
ESM Artifact Check:
  User Journey              | ✅ docs/features/user_journey.md (3.9KB)
  Dialogue Maps             | ✅ docs/ux/dialogue-map.md (1.4KB, mermaid; no GUI screens)
  Feature Files             | ✅ docs/features/act-1-bridge/ (6 .feature files)
  IA Guidelines             | ✅ docs/ux/IA_guidelines.md (1.7KB; CLI + Entourage; UI: None)
```

Stock ESM expected draw.io mockups. Drift: SAO §1 has no web UI — dialogue map + IA are operator/client protocol surfaces.

## DSP-02 DTA artifacts

```
DTA Artifact Check:
  SAO.md exists              | ✅ docs/architecture/SAO.md (15.8KB)
  Executive Summary          | ✅ Present
  System Architecture        | ✅ §1 Application Blocks + §2 Integration
  Design Principles          | ✅ Present (daemon / tosser split)
  Technology Stack           | ✅ Technology Stack Table (Python 3.14)
  Project Structure          | ✅ §3 Code Organization
  Testing Infrastructure     | ✅ §5 Test Strategy (daemon Trophy)
```

DTA-18 (MCP) and DTA-19 (AI agents / SAO §17) are **N/A** for v1. No redirect.

## DSP-03 architecture & code organization

```
Architecture & Code Organization Check:
  Technology stack defined   | ✅ Python 3.14 package, sqlite, Celery, httpx/msal, aiosmtpd, Twisted POP3
  Directory layout defined   | ✅ SAO §3
  Project structure exists   | ✅ o365pop/, tests/, docs/, Makefile, pyproject.toml, .venv
  CI/CD config               | ✅ .github/workflows/ci.yml (merge gate; no CD E2E)
  BPE workflow available     | ✅ .cursor/playbooks/edda/BPE/ (9 activities)
  Skills available           | ✅ 30 skills in .cursor/playbooks/edda/skills/
  Artifact templates         | ✅ 39 templates in .cursor/playbooks/edda/artifacts/
  TFK in this export         | ✅ .cursor/playbooks/edda/TFK/ (9 activities)
```

## DSP-04 target AI IDE

```
Target AI IDE Selection:
  Primary:   Cursor
  Secondary: none

  Output files to generate:
    1. .cursor/rules/_ai-context.mdc  (DSP-05; existing project rules not overwritten)
```

Existing `.cursor/rules/*.mdc` (including `o365pop-stack-locks.mdc`) stay. No `.github/copilot-instructions.md`. No Windsurf tree. No DSP-generated `CLAUDE.md`.

## DSP-05 generated config

| File | Status |
|------|--------|
| `.cursor/rules/_ai-context.mdc` | Regenerated from SAO + Edda v73 inventory |
| `AGENTS.md` | Pointers + ADE status |
| `docs/process/MODUS_OPERANDI.md` | Target ADE + next scenario |

Ten DSP-05 sections in `_ai-context.mdc`: What Is, Architecture, Docs Map, Workflows, Skills, Artifact Templates, AI/Human, Conventions, BPE, Running Locally.

Agent-lane inventory **omitted** (SAO §17 N/A).

## DSP-06 review & commit

| Check | Result |
|-------|--------|
| Completeness | 10 sections present |
| Accuracy | Matches SAO.md 2026-09-05 |
| Docs map | Referenced paths exist |
| Workflows | All 11 Edda v73 workflows listed with correct activity counts |
| Skills | 30 listed; Django/HTMX/Playwright/K8s/CDK marked N/A |
| Artifact templates | 39 listed; cloud/UI templates marked N/A |
| Conventions | Pointers to `.cursor/rules/` — bodies not duplicated |
| Running locally | `make provision` / `make test` / `make status` / `make login` |

DSP is complete. BSP already done. Next process workflow: TFK (see `docs/process/TFK_VERIFICATION.md`).

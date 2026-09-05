# CI Pipeline (GitHub Actions)

**Type**: Document
**Required**: No
**Produced by**: Build CI Pipeline

# CI Pipeline (GitHub Actions)

**Artifact ID**: 12
**Type**: Code
**Required**: True

## Description

# ==============================================================================
# Artifact: CI Pipeline — GitHub Actions
# Workflow: DCD — Design & Deploy CICD
#
# Thin wrapper around `make` targets. No business logic in YAML.
# Copy to {project}/.github/workflows/ci.yml
# ==============================================================================

name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  id-token: write
  contents: read

env:
  PYTHON_VERSION: '3.12'
  NODE_VERSION: '20'

jobs:
  # --------------------------------------------------------------------------
  # Test — runs on every push and PR
  # --------------------------------------------------------------------------
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: make provision

      - name: Lint
        run: make lint

      - name: Unit tests
        run: make test

      - name: Integration tests
        run: make test-integration

  # --------------------------------------------------------------------------
  # Build — only on main after tests pass (not on PRs)
  # --------------------------------------------------------------------------
  build:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Build and push containers
        run: make containers

      - name: Output image tag
        run: echo "Image tag: $(git rev-parse --short HEAD)"

# ==============================================================================
# Optional: Agent eval workflow (separate file — do NOT merge into ci.yml)
# ==============================================================================
#
# **Default ci.yml above is UNCHANGED.** Agent-less projects and baseline PR flow
# keep unit + integration (+ AT when added) as the only merge gate.
#
# When SAO §17 applies:
#   - Lane 1 (optional PR): append conditional step to ci.yml — see below
#   - Lanes 3–4: copy to {project}/.github/workflows/agent-eval.yml
#
# --- Optional PR extension (agents only) — append to ci.yml test job ---
#
#      - name: Agent control-plane proofs (lane 1)
#        if: vars.AGENTS_ENABLED == 'true'
#        env:
#          AGENTS_ENABLED: true
#        run: make test-agent-proof
#
# Do not add `-m agent_proof` unconditionally — empty collection fails CI.
# Enable the step only after at least one PRF test exists.

# ==============================================================================
# agent-eval.yml — documented example (workflow_dispatch + schedule)
# Copy to {project}/.github/workflows/agent-eval.yml
# ==============================================================================

```yaml
name: Agent Eval

on:
  workflow_dispatch:
  schedule:
    - cron: '0 6 * * *'   # nightly lane 3 contract eval

permissions:
  contents: read

env:
  PYTHON_VERSION: '3.12'

jobs:
  live-contract:
    if: vars.AGENT_EVAL_ENABLED == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: make provision

      - name: Lane 3 — live contract eval (temp=0)
        env:
          AGENTS_ENABLED: true
          LIVE_LLM_API_KEY: ${{ secrets.LIVE_LLM_API_KEY }}
        run: make test-agent-eval

  task-quality:
    if: vars.AGENT_EVAL_ENABLED == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: make provision

      - name: Lane 4 — TASK golden quality band
        env:
          AGENTS_ENABLED: true
          LIVE_LLM_API_KEY: ${{ secrets.LIVE_LLM_API_KEY }}
        run: make test-agent-quality
```

**Gate summary:**

| Workflow | Lane | Blocks PR merge? |
|----------|------|------------------|
| `ci.yml` (default) | unit + integration (+ AT) | Yes — unchanged |
| `ci.yml` optional step | 1 `@agent_proof` | Yes — only when `AGENTS_ENABLED` |
| `agent-eval.yml` | 3 `@live_llm`, 4 `@quality` | No — nightly / manual / promotion |

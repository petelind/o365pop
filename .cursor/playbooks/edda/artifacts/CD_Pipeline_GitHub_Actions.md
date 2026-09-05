# CD Pipeline (GitHub Actions)

**Type**: Document
**Required**: No
**Produced by**: Build CD Pipeline

# CD Pipeline (GitHub Actions)

**Artifact ID**: 13
**Type**: Code
**Required**: True

## Description

# ==============================================================================
# Artifact: CD Pipeline — GitHub Actions
# Workflow: DCD — Design & Deploy CICD
#
# Thin wrapper around `make` targets. No business logic in YAML.
# Copy to {project}/.github/workflows/cd.yml
#
# Flow: deploy to idle → smoke test → manual approval → switch traffic
# ==============================================================================

name: CD

on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [main]
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Image tag to deploy (default: latest main SHA)'
        required: false
        default: ''
      target_env:
        description: 'Target environment (auto-detects idle if empty)'
        required: false
        default: ''

permissions:
  id-token: write
  contents: read

env:
  PYTHON_VERSION: '3.12'

jobs:
  # --------------------------------------------------------------------------
  # Deploy to idle environment
  # --------------------------------------------------------------------------
  deploy-idle:
    if: >-
      github.event_name == 'workflow_dispatch' ||
      github.event.workflow_run.conclusion == 'success'
    runs-on: ubuntu-latest
    environment: staging
    outputs:
      idle_env: ${{ steps.detect.outputs.idle }}
      image_tag: ${{ steps.tag.outputs.tag }}
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: make provision

      - name: Configure kubectl
        run: aws eks update-kubeconfig --name ${{ vars.EKS_CLUSTER }} --region ${{ vars.AWS_REGION }}

      - name: Determine image tag
        id: tag
        run: |
          TAG="${{ github.event.inputs.image_tag }}"
          if [ -z "$TAG" ]; then
            TAG=$(git rev-parse --short HEAD)
          fi
          echo "tag=$TAG" >> $GITHUB_OUTPUT
          echo "Using image tag: $TAG"

      - name: Detect idle environment
        id: detect
        run: |
          TARGET="${{ github.event.inputs.target_env }}"
          if [ -z "$TARGET" ]; then
            # Default: deploy to green (idle) — adjust based on your traffic state
            TARGET="green"
          fi
          echo "idle=$TARGET" >> $GITHUB_OUTPUT
          echo "Deploying to: $TARGET"

      - name: Deploy to idle
        env:
          IMAGE_TAG: ${{ steps.tag.outputs.tag }}
        run: make deploy ENV=${{ steps.detect.outputs.idle }}

  # --------------------------------------------------------------------------
  # Smoke tests on idle
  # --------------------------------------------------------------------------
  smoke-test:
    needs: deploy-idle
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: make provision

      - name: Smoke tests on idle
        run: make smoke-test ENV=idle

  # --------------------------------------------------------------------------
  # Manual approval → switch production traffic
  # --------------------------------------------------------------------------
  switch:
    needs: smoke-test
    runs-on: ubuntu-latest
    environment: production  # REQUIRES MANUAL APPROVAL
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: make provision

      - name: Switch traffic to new deployment
        run: make switch

      - name: Verify production
        run: make smoke-test ENV=prod

      - name: Final status
        run: make pipeline-status

# ==============================================================================
# Optional pre-swap job — agent contract cert (lane 3)
# ==============================================================================
#
# Append when SAO §17 applies. Gated on repository variable AGENT_EVAL_ENABLED.
# Default cd.yml above is UNCHANGED for agent-less projects.
#
# Insert after smoke-test job; wire switch job to `needs: [smoke-test, agent-contract-cert]`
# only when this job is present. When AGENT_EVAL_ENABLED is unset, agent-contract-cert
# is skipped and switch may keep `needs: smoke-test` only.

```yaml
  agent-contract-cert:
    needs: smoke-test
    if: vars.AGENT_EVAL_ENABLED == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: make provision

      - name: Lane 3 — live contract eval (temp=0, not ScriptedLLM)
        env:
          AGENTS_ENABLED: true
          LIVE_LLM_API_KEY: ${{ secrets.LIVE_LLM_API_KEY }}
          STAGING_BASE_URL: ${{ vars.STAGING_URL }}
        run: make test-agent-eval

  switch:
    needs: [smoke-test, agent-contract-cert]
    # When agent cert disabled, use: needs: smoke-test
```

**Notes:**
- Lane 3 asserts contract bounds only — see artifact 56 Part 3.4.
- Failure here is a promotion signal, not a default merge blocker.
- Lane 4 (`make test-agent-quality`) remains on `agent-eval.yml` / manual promotion — not in CD swap path by default.

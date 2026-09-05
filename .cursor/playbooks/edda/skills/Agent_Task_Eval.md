# Agent Task Eval

**Capability**: —
**Stack**: —

# Skill: Agent Task Eval

**Capability Domain**: TEST_INTEGRATION
**Technology Stack**: pytest, golden-tasks, optional-deepeval
**Linked Activities**: TFK-04, TFK-05, TFK-09, DTA-19

## Overview

Patterns for **lane 4** (task performance quality): frozen tasks with structured ground truth.

## Principles

1. Structured oracle is source of truth.
2. Same harness as lane 1; live provider at temp=0.
3. Not a PR merge gate — promotion band vs last certified baseline.
4. Deepeval optional overlay for fuzzy SC-01 only.

## Golden task catalog

See artifact 56 Part 4.6 — TASK-* under `tests/fixtures/agent_tasks/`.

## Makefile / CI

`make test-agent-quality` gated on `AGENTS_ENABLED`; separate `agent-eval.yml`.

## References

Artifact 56 Part 4.6; DTA-19 §16.

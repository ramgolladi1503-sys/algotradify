# CI Agent Architecture Gate

## Status

Agent Governance PR 15.

This document describes the GitHub Actions gate for the role-based mini-agent architecture.

## Scope

PR 15 wires the existing governance contracts into CI.

It does not add:

```text
changed-file auditor
PR template gate
architecture audit report
agent worker
auto-merge
mobile approval
broker behavior
paper execution behavior
live config mutation
runtime execution behavior
```

Those belong to later PRs in the locked PR 11–18 order.

## Workflow

Workflow file:

```text
.github/workflows/agent-architecture-ci.yml
```

The workflow runs on:

```text
pull_request to main
workflow_dispatch
```

## CI checks

The workflow runs focused governance tests:

```bash
python -m pytest \
  tests/test_agent_role_registry.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_handoff_contract.py \
  tests/test_agent_handoff_validator.py \
  tests/test_agent_architecture_gate.py \
  -q
```

Then it runs the architecture gate:

```bash
python scripts/run_agent_architecture_gate.py --task-ref "${{ github.event.pull_request.title }}" --json
```

For manual dispatch:

```bash
python scripts/run_agent_architecture_gate.py --task-ref "${{ github.event.inputs.task_ref }}" --json
```

## Gate checks

The gate validates:

```text
role registry is valid
workflow state machine is valid
handoff artifact contract is present
handoff evidence files are valid for the resolved task id
```

## Task ID resolution

The gate can resolve task references such as:

```text
AGENT-PR15
agent-pr15
Agent PR 15
Agent PR 15: Add CI Agent Architecture Gate
```

## Safe flags

Every gate report preserves:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
real_order_id=null
allowed_for_runtime_wiring=false
allowed_for_broker_api=false
```

## What PR 15 deliberately does not do

PR 15 does not audit changed files.

PR 15 does not enforce PR template content.

PR 15 does not generate architecture replay reports.

PR 15 does not call broker APIs, mutate runtime state, or add dashboard behavior.

Those enforcement features belong to PR 16–18.

## Next PR

PR 16 — Changed-File Scope Auditor.

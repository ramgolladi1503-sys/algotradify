# Role Handoff Artifact Contract

## Status

Agent Governance PR 13.

This document describes the single-artifact handoff contract for the role-based mini-agent architecture.

## Scope

PR 13 defines the handoff artifact payload contract only.

It does not add:

```text
repo-wide handoff validator
CI architecture gate
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

## Required fields

Every role handoff artifact payload must include:

```text
schema_version
contract
task_id
role_id
workflow_state
target_state
scope_decision
files_allowed
files_forbidden
risks_found
tests_required
acceptance_gates
required_outputs
verdict
safe_flags
```

Optional but supported fields:

```text
blockers
warnings
metadata
```

## Verdicts

```text
APPROVED
APPROVED_WITH_WARNINGS
REJECTED
BLOCKED
```

A blocking verdict requires at least one blocker.

## Safe flags

Every handoff artifact must preserve:

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

## Role required outputs

The handoff artifact must include all required outputs for its role from the role registry.

Examples:

```text
Hermes handoff must include architecture_decision, contract_boundaries, files_to_change, files_not_to_touch, acceptance_gates.
GSD handoff must include patch_summary, changed_files, tests_added, test_commands, implementation_boundary.
```

## Contract functions

The implementation exposes:

```text
normalize_agent_handoff_artifact(...)
validate_agent_handoff_payload(...)
build_minimal_handoff_payload(...)
agent_handoff_schema_contract()
```

## Behavior guarantees

PR 13 tests prove:

```text
valid handoff payload normalizes successfully
missing required fields fail closed
unknown role fails closed
unknown workflow state fails closed
unknown verdict fails closed
unsafe safe flags fail closed
missing role-required outputs fail closed
blocking verdict without blockers fails closed
validate helper returns valid=false instead of raising
```

## What PR 13 deliberately does not do

PR 13 does not scan `docs/pr-handoffs/`.

PR 13 does not compare a PR body against required handoffs.

PR 13 does not inspect changed files.

PR 13 does not update GitHub Actions.

Those enforcement features start at PR 14 and later.

## Next PR

PR 14 — PR Handoff Evidence Validator.

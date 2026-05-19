# Agent Role Registry Contract

## Status

Agent Governance PR 11.

This document describes the role registry contract added for the role-based mini-agent architecture enforcement wave.

## Scope

PR 11 adds role contracts only.

It does not add:

```text
workflow state machine
handoff artifact validator
CI architecture gate
changed-file auditor
PR template gate
architecture audit report
agent worker
auto-merge
mobile approval
broker action
paper order trigger
live config mutation
runtime execution behavior
```

Those belong to later PRs in the locked PR 11–18 order.

## Purpose

The role registry turns named mini-agent roles into enforceable contracts.

A role is not a personality. A role defines:

```text
allowed source agents
allowed actions
forbidden actions
allowed path prefixes
forbidden path prefixes
required outputs
handoff targets
safe flags
```

## Roles

The PR 11 registry defines these locked roles:

```text
scope_owner
grill_reviewer
hermes_architect
gsd_implementer
qa_safety_reviewer
evidence_recorder
human_approver
```

## Role boundaries

### Scope Owner

Owns task boundary, files allowed, files forbidden, non-goals, and reject conditions.

May not implement patches or bypass safety review.

### Grill Reviewer

Challenges weak assumptions, fake progress, overengineering, missing proof, and scope drift.

May not generate implementation patches.

### Hermes Architect

Defines architecture, contracts, file boundaries, and acceptance gates.

May not generate implementation patches or approve merge.

### GSD Implementer

Generates scoped tests, scoped patches, fixes scoped test failures, and updates scoped documentation.

May not expand scope, touch forbidden paths, call brokers, change live config, or auto-merge.

### QA/Safety Reviewer

Reviews test strength, changed-file scope, safety flags, and broker/live/order boundaries.

May not act as implementation owner in the same role.

### Evidence Recorder

Records commands, test results, acceptance proof, safety boundary, and reject conditions.

May not approve merge alone.

### Human Approver

Decides merge-readiness only after required role evidence and safety gates pass.

May not silently bypass safety blockers.

## Safe flags

Every role contract preserves:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
real_order_id=null
```

The role registry never grants:

```text
allowed_for_runtime_wiring=true
allowed_for_broker_api=true
allowed_for_live_execution=true
```

## Forbidden actions

Every role forbids trading/live/broker actions:

```text
PLACE_ORDER
MODIFY_ORDER
CANCEL_ORDER
EXIT_POSITION
ENABLE_LIVE
DISABLE_RISK_GATE
CHANGE_BROKER_CONFIG
CHANGE_LIVE_CONFIG
CALL_BROKER_API
```

## Forbidden paths

Every role blocks known forbidden path prefixes:

```text
.env
credentials.py
config/secrets
runtime/live
logs/broker
broker_contract/
execution_safety/live
execution_readiness/live
paper_broker/live
```

## High-risk paths

Requests touching these paths require explicit human approval where the role allows the path:

```text
agent_system/
api/
config/
core/
execution_readiness/
execution_safety/
main.py
paper_trading/
run_live.sh
runtime_contract.py
```

## Contract functions

The implementation exposes:

```text
build_agent_role_registry()
get_agent_role_contract(role_id)
assess_role_request(...)
agent_role_registry_schema_contract()
validate_agent_role_registry()
```

## Behavior guarantees

PR 11 tests prove:

```text
all locked roles exist
no role allows forbidden trading/live/broker actions
Hermes cannot generate patches
Grill cannot generate code
GSD can generate scoped patches only with approval for high-risk paths
GSD cannot touch broker/live paths even with human approval
QA/Safety cannot modify implementation
Evidence Recorder cannot approve merge
Human Approver cannot bypass forbidden actions
unknown roles fail closed
```

## Next PR

PR 12 — Role-Based Workflow State Machine.

PR 12 must define lifecycle transitions. PR 11 only defines role contracts.

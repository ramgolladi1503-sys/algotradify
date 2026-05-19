# Hermes Handoff — Agent PR 11

## Role

Hermes Architect

## Verdict

APPROVED_ARCHITECTURE

## Architecture decision

Add a pure role registry layer for the locked role-based mini-agent architecture.

This PR defines roles and role-level permission contracts only. It must not implement workflow transitions, handoff validation, CI gates, changed-file auditing, PR templates, or audit reports.

## Files to change

```text
agent_system/role_registry.py
agent_system/role_contracts.py
agent_system/__init__.py
tests/test_agent_role_registry.py
docs/agent-role-registry.md
docs/pr-handoffs/AGENT-PR11-grill.md
docs/pr-handoffs/AGENT-PR11-hermes.md
docs/pr-handoffs/AGENT-PR11-gsd.md
PROJECT_STATE.md
```

## Files not to touch

```text
api/
frontend/
dashboard/
paper_trading/
broker_contract/
execution_safety/
execution_readiness/
strategies/
movement_engine/
top_selector/
main.py
run_live.sh
runtime_contract.py
.github/workflows/
```

## Contract boundaries

The role registry must expose:

```text
build_agent_role_registry
get_agent_role_contract
assess_role_request
agent_role_registry_schema_contract
validate_agent_role_registry
```

## Role contracts

The locked roles are:

```text
scope_owner
grill_reviewer
hermes_architect
gsd_implementer
qa_safety_reviewer
evidence_recorder
human_approver
```

## Acceptance gates

```text
all locked roles exist
no role grants runtime wiring
no role grants external service action rights
no role grants live execution rights
role/action/source mismatch fails closed
protected paths fail closed
high-risk paths require human approval
tests prove behavior, not just object shape
```

## Non-goals

```text
workflow state machine
handoff validator
CI architecture gate
changed-file auditor
PR template gate
architecture audit report
agent worker
auto-merge
mobile approval
runtime execution behavior
```

## Safe flags

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
real_order_id=null
```

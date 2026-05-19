# Hermes Handoff — Agent PR 13

## Role

Hermes Architect

## Verdict

APPROVED_ARCHITECTURE

## Architecture decision

Add a single-payload role handoff artifact contract for the role-based mini-agent architecture.

This PR defines the handoff payload schema and in-memory normalization only. It must not scan `docs/pr-handoffs/`, compare PR bodies, inspect changed files, update CI, or decide merge-readiness.

## Files to change

```text
agent_system/handoff_contract.py
agent_system/__init__.py
tests/test_agent_handoff_contract.py
docs/agent-handoff-artifact-contract.md
docs/pr-handoffs/AGENT-PR13-grill.md
docs/pr-handoffs/AGENT-PR13-hermes.md
docs/pr-handoffs/AGENT-PR13-gsd.md
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

The handoff contract must expose:

```text
normalize_agent_handoff_artifact
validate_agent_handoff_payload
build_minimal_handoff_payload
agent_handoff_schema_contract
```

## Required fields

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

## Acceptance gates

```text
all required fields are enforced
unknown roles fail closed
unknown workflow states fail closed
unknown verdicts fail closed
safe flags are mandatory
role-required outputs are mandatory
blocking verdict requires blockers
no repo-wide validation is added
```

## Non-goals

```text
repo-wide handoff validator
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

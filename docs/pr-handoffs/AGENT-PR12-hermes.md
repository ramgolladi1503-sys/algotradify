# Hermes Handoff — Agent PR 12

## Role

Hermes Architect

## Verdict

APPROVED_ARCHITECTURE

## Architecture decision

Add a deterministic in-memory workflow state machine for the locked role-based mini-agent architecture.

This PR defines state order and transition rules only. It must not implement handoff artifact validation, CI gates, changed-file auditing, PR template enforcement, or architecture reports.

## Files to change

```text
agent_system/workflow_state.py
agent_system/__init__.py
tests/test_agent_workflow_state.py
docs/agent-workflow-state-machine.md
docs/pr-handoffs/AGENT-PR12-grill.md
docs/pr-handoffs/AGENT-PR12-hermes.md
docs/pr-handoffs/AGENT-PR12-gsd.md
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

The workflow state machine must expose:

```text
evaluate_agent_workflow_transition
replay_agent_workflow
agent_workflow_state_schema_contract
validate_agent_workflow_state_machine
```

## Ordered flow

```text
REQUESTED
SCOPED_BY_SCOPE_OWNER
REVIEWED_BY_GRILL
DESIGNED_BY_HERMES
IMPLEMENTED_BY_GSD
REVIEWED_BY_QA_SAFETY
EVIDENCE_RECORDED
HUMAN_APPROVED
MERGE_READY
```

## Terminal blocked states

```text
BLOCKED_SCOPE
BLOCKED_SAFETY
BLOCKED_MISSING_EVIDENCE
BLOCKED_FORBIDDEN_PATH
BLOCKED_UNAPPROVED_PATCH
```

## Acceptance gates

```text
role owns exactly one normal transition
merge-ready requires human approver role
merge-ready requires human-approved state
merge-ready requires outputs, safety, evidence, and human approval
blocked states cannot continue
unknown roles and states fail closed
safe flags remain non-executing
```

## Non-goals

```text
handoff artifact validator
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

# Role-Based Workflow State Machine

## Status

Agent Governance PR 12.

This document describes the deterministic role-based workflow state machine for the mini-agent architecture.

## Scope

PR 12 adds workflow state evaluation only.

It does not add:

```text
handoff artifact validator
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

## Ordered active states

```text
REQUESTED
→ SCOPED_BY_SCOPE_OWNER
→ REVIEWED_BY_GRILL
→ DESIGNED_BY_HERMES
→ IMPLEMENTED_BY_GSD
→ REVIEWED_BY_QA_SAFETY
→ EVIDENCE_RECORDED
→ HUMAN_APPROVED
→ MERGE_READY
```

## Terminal blocked states

```text
BLOCKED_SCOPE
BLOCKED_SAFETY
BLOCKED_MISSING_EVIDENCE
BLOCKED_FORBIDDEN_PATH
BLOCKED_UNAPPROVED_PATCH
```

Blocked states are terminal. Once a workflow reaches a blocked state, it cannot continue through normal transitions.

## Role-owned transitions

```text
scope_owner: REQUESTED → SCOPED_BY_SCOPE_OWNER
grill_reviewer: SCOPED_BY_SCOPE_OWNER → REVIEWED_BY_GRILL
hermes_architect: REVIEWED_BY_GRILL → DESIGNED_BY_HERMES
gsd_implementer: DESIGNED_BY_HERMES → IMPLEMENTED_BY_GSD
qa_safety_reviewer: IMPLEMENTED_BY_GSD → REVIEWED_BY_QA_SAFETY
evidence_recorder: REVIEWED_BY_QA_SAFETY → EVIDENCE_RECORDED
human_approver: EVIDENCE_RECORDED → HUMAN_APPROVED
human_approver: HUMAN_APPROVED → MERGE_READY
```

## Required gates

The state machine rejects transitions when required proof is absent:

```text
required_outputs_present=false blocks normal role transitions
safety_review_passed=false blocks QA/Safety and final merge-readiness
 evidence_recorded=false blocks evidence and final merge-readiness
human_approved=false blocks human approval and final merge-readiness
```

## Examples of blocked jumps

```text
REQUESTED → IMPLEMENTED_BY_GSD is rejected.
DESIGNED_BY_HERMES → MERGE_READY is rejected.
IMPLEMENTED_BY_GSD → HUMAN_APPROVED is rejected.
MERGE_READY by any role except human_approver is rejected.
```

## Contract functions

The implementation exposes:

```text
evaluate_agent_workflow_transition(...)
replay_agent_workflow(...)
agent_workflow_state_schema_contract()
validate_agent_workflow_state_machine()
```

## Safe flags

Every workflow decision preserves:

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

## Behavior guarantees

PR 12 tests prove:

```text
happy path reaches MERGE_READY only in correct order
REQUESTED cannot jump directly to GSD implementation
Hermes design cannot jump to merge-ready
GSD implementation cannot jump directly to human approval
QA/Safety transition requires safety review pass
Evidence transition requires evidence flag
Human approval transition requires human approval flag
Final merge-ready requires outputs, safety, evidence, and human approval
blocked states are terminal
workflow replay stops on first rejection or blocked state
unknown roles and states fail closed
```

## Next PR

PR 13 — Role Handoff Artifact Contract.

PR 13 must define handoff artifact schemas. PR 12 only defines state order and transition rules.

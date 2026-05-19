# Grill Handoff — Agent PR 12

## Role

Grill Reviewer

## Verdict

APPROVED_WITH_STRICT_SCOPE

## Scope reviewed

Agent PR 12 — Role-Based Workflow State Machine.

## Risks found

1. A workflow state machine can become fake governance if it only documents an order but does not reject invalid jumps.
2. If GSD can move directly from requested to implemented, the role flow is meaningless.
3. If merge-ready can happen before evidence and human approval, the architecture is bypassable.
4. If blocked states are not terminal, reviewers can ignore safety failures.
5. If PR 12 adds handoff parsing, changed-file auditing, or CI behavior, it violates the locked PR order.

## Required blockers

PR 12 must block:

```text
REQUESTED to IMPLEMENTED_BY_GSD
DESIGNED_BY_HERMES to MERGE_READY
IMPLEMENTED_BY_GSD to HUMAN_APPROVED
MERGE_READY without human approval
MERGE_READY without evidence
MERGE_READY without safety review
transition from terminal blocked state
unknown role
unknown state
```

## Required proof

Tests must prove behavior, not just schema shape:

```text
happy path reaches MERGE_READY only in order
bad jumps stay at current state
blocked states are terminal
workflow replay stops after first rejection
safe flags remain false/null
```

## Rejection conditions

Reject this PR if it adds:

```text
handoff artifact validator
CI architecture gate
changed-file auditor
PR template gate
architecture audit report
auto-merge
mobile approval
agent worker
broker/live/order behavior
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

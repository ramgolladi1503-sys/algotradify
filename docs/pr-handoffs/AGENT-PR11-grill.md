# Grill Handoff — Agent PR 11

## Role

Grill Reviewer

## Verdict

APPROVED_WITH_STRICT_SCOPE

## Scope reviewed

Agent PR 11 — Agent Role Registry Contract.

## Risks found

1. Role registry can become fake governance if it only snapshots object shapes.
2. If implementation roles can touch protected trading/runtime paths, the architecture becomes unsafe.
3. If architect/reviewer roles can generate implementation patches, role separation collapses.
4. If final approval can ignore blocked safety conditions, the gate becomes theatre.
5. If PR 11 accidentally adds workflow state machine or CI gates, it violates the locked PR order.

## Required blockers

PR 11 must block:

```text
Hermes generating patches
Grill generating code
GSD touching protected trading/runtime paths
QA/Safety modifying implementation as reviewer
Evidence Recorder approving merge
Human Approver using forbidden trading/runtime actions
unknown roles
missing requested paths
```

## Required proof

Tests must prove behavior, not just schema shape:

```text
role registry has exact locked roles
forbidden actions are absent from every role
safe flags remain false/null
role/action/source mismatches fail
forbidden paths fail
high-risk paths require human approval
```

## Rejection conditions

Reject this PR if it adds:

```text
workflow state machine
handoff validator
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

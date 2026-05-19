# Grill Handoff — Agent PR 13

## Role

Grill Reviewer

## Verdict

APPROVED_WITH_STRICT_SCOPE

## Scope reviewed

Agent PR 13 — Role Handoff Artifact Contract.

## Risks found

1. A handoff contract can become fake governance if it only documents fields but does not fail unsafe payloads.
2. If safe flags are optional, future handoffs can hide risky behavior.
3. If role-required outputs are not checked, roles can submit empty evidence and still look complete.
4. If blocking verdicts do not require blockers, rejected work has no useful reason trail.
5. If PR 13 scans the repo or validates PR evidence globally, it violates the locked PR order and steals PR 14 scope.

## Required blockers

PR 13 must block:

```text
missing required fields
wrong contract
wrong schema version
unknown role
unknown workflow state
unknown verdict
unsafe safe flags
missing role-required outputs
blocking verdict without blockers
invalid list fields
empty required evidence lists
```

## Required proof

Tests must prove behavior, not just schema shape:

```text
valid handoff normalizes
missing fields fail closed
unsafe flags fail closed
role outputs are required
blocking verdict requires blockers
validate helper returns valid=false for bad payloads
```

## Rejection conditions

Reject this PR if it adds:

```text
repo-wide handoff validator
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

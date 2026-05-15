# Approval Creation and Validation

Approval creation turns an operator decision into append-only approval audit evidence.

## Hard rule

Approval creation is not execution.

This layer does not:

- place orders
- call broker APIs
- submit orders
- modify orders
- cancel orders
- exit positions
- bypass execution safety

It validates and writes approval evidence only.

## Implemented package

```text
approval_audit/creation.py
```

## Core helpers

```text
ApprovalCreationRequest
ApprovalCreationResult
validate_approval_creation(...)
create_approval_event(...)
append_approval_event(...)
approval_request_from_mapping(...)
```

## Required fields

```json
{
  "candidate_id": "c1",
  "operator_id": "op1",
  "reason": "manual risk review completed",
  "expires_at_epoch": 200,
  "ts_epoch": 100,
  "safety_decision": {
    "execution_permitted": false,
    "status": "BLOCKED",
    "is_order_action": false,
    "safety_visibility_only": true
  }
}
```

## Validation blockers

```text
CANDIDATE_ID_REQUIRED
OPERATOR_ID_REQUIRED
APPROVAL_REASON_TOO_SHORT
APPROVAL_EXPIRY_REQUIRED
APPROVAL_EXPIRY_MUST_BE_AFTER_TIMESTAMP
APPROVAL_STATUS_MUST_BE_APPROVED_OR_REJECTED
SAFETY_DECISION_SNAPSHOT_REQUIRED
SAFETY_DECISION_EXECUTION_PERMITTED_REQUIRED
SAFETY_DECISION_STATUS_REQUIRED
SAFETY_DECISION_ORDER_FLAG_UNSAFE
APPROVAL_ID_TOO_SHORT
```

## Warnings

```text
SAFETY_DECISION_VISIBILITY_FLAG_MISSING
```

## Append-only writer

`append_approval_event(path, request)` appends one JSON line to an audit file.

Recommended path:

```text
.runtime/approval_audit.jsonl
```

## Current limitation

This PR adds the validated creation helper and append-only writer only.

It does not add a POST endpoint yet. That keeps the approval mutation surface out of the API until the contract is stable and reviewed.

Next expected work:

1. POST /approval-audit with strict validation
2. approval card in Control Tower
3. dry-run execution adapter

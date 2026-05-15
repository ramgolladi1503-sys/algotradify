# Approval Audit Log

Approval audit records manual approval evidence. It does not approve trades by itself and does not place orders.

## Goal

Make every approval decision traceable before dry-run or paper execution exists.

The audit log answers:

- who approved or rejected
- when the decision happened
- which candidate was involved
- why the decision was made
- when the approval expires
- what execution-safety snapshot existed at approval time
- whether the event is immutable audit evidence

## Implemented package

```text
approval_audit/
  __init__.py
  audit.py
```

## API

```bash
curl http://localhost:8000/approval-audit
curl 'http://localhost:8000/approval-audit?candidate_id=c1'
curl 'http://localhost:8000/approval-audit?candidate_id=c1&now_epoch=100'
```

## Supported artifact filenames

JSON artifacts:

```text
approval_audit_latest.json
approval_audit_events_latest.json
approvals_latest.json
manual_approvals_latest.json
```

JSONL artifacts:

```text
approval_audit.jsonl
approval_audit_events.jsonl
approvals.jsonl
manual_approvals.jsonl
```

Files can live under:

```text
.runtime/
.runtime/logs/
```

## Supported statuses

```text
APPROVED
REJECTED
EXPIRED
REVOKED
UNKNOWN
```

Common aliases such as `ALLOW`, `DENIED`, and `CANCELED` are normalized.

## Required fields per event

```json
{
  "approval_id": "a1",
  "candidate_id": "c1",
  "operator_id": "op1",
  "status": "APPROVED",
  "reason": "manual risk review",
  "ts_epoch": 100,
  "expires_at_epoch": 200,
  "safety_decision": {
    "execution_permitted": false,
    "status": "BLOCKED"
  }
}
```

## Response fields

```text
candidate_id
current_status
approval_id
operator_id
approved_count
rejected_count
expired_count
revoked_count
latest_reason
events
blockers
warnings
is_order_action
```

Each event also exposes:

```text
immutable_audit_event
is_order_action
```

## Safety boundary

This layer does not:

- place orders
- call broker APIs
- submit orders
- modify orders
- cancel orders
- exit positions
- bypass execution safety
- create approval mutations

It reads approval evidence only.

## Current limitation

The API is read-only. Approval creation and signed approval persistence are intentionally not implemented yet.

Next expected work after this layer:

1. approval creation command/API with strict validation
2. dry-run execution adapter
3. paper execution flow

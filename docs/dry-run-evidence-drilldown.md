# Dry-Run Evidence Drilldown

PR 30 adds a richer read-only dry-run explanation panel to the Control Tower.

## Purpose

The operator should not need to guess why a dry-run was created or blocked. The Control Tower now surfaces the evidence chain behind the dry-run result.

## Displayed evidence

The dry-run card shows:

- created state
- dry-run-only flag
- non-order-action flag
- broker API call flag
- dry-run id
- real order id
- blockers
- warnings
- operator explanation
- selected candidate snapshot
- execution safety snapshot
- approval snapshot
- readiness snapshot
- outcome event

## Operator explanation

The UI explains:

- dry-run created from selected candidate, safety, approval, and readiness evidence
- blocked dry-run with upstream blockers
- unavailable dry-run when evidence is missing

## Safety boundary

This is a visibility-only panel.

The frontend calls:

```text
GET /dry-run-execution?limit=20
```

The frontend does not call append mode and does not create mutation controls.

Forbidden behavior:

- external execution controls
- broker controls
- submit/modify/cancel/exit controls
- artifact append from frontend

## Tests

`tests/test_control_tower_ui.py` verifies the endpoint, dry-run card, operator explanation, evidence snapshots, and no frontend append call.

# Production Execution-Safety Design

This document defines the safety boundary before Algotradify can expose any execution controls.

## Hard rule

Execution safety design is not broker execution.

This layer must not:

- place orders
- call broker order APIs
- modify orders
- cancel orders
- exit positions
- bypass execution readiness

## Required gates before execution is permitted

1. Top executable candidate must exist.
2. Execution readiness must be allowed.
3. Manual approval must exist when required.
4. Operator identity must exist when manual approval is required.
5. Broker confirmation must exist when required.
6. Dry-run requirement must be cleared explicitly.
7. Kill switch must be off.
8. Daily loss guard must not be breached.
9. Daily order-count guard must not be breached.
10. Quantity guard must not be breached.
11. Warnings must be acknowledged.

## Modes

### PAPER

Paper mode may be permitted when all configured safety gates pass. It still produces an execution-safety decision only. It does not place broker orders.

### LIVE

Live mode is allowed only after strict approval and broker confirmation gates pass. Live mode must always surface `LIVE_MODE_REQUIRES_STRICT_APPROVAL` as a warning.

## Kill switch

When `kill_switch_enabled=true`, execution is blocked regardless of all other evidence.

## Approval model

Manual approval requires:

- `approval_id`
- `operator_id`

Missing either blocks execution.

## Broker confirmation gate

When broker confirmation is required, `broker_confirmation_id` must be present. This prevents confusing selected candidates with confirmed broker-side readiness.

## Guard rails

The policy supports:

- `max_daily_loss`
- `current_daily_loss`
- `max_orders_per_day`
- `orders_today`
- `max_quantity`
- `requested_quantity`

Breaching any configured guard blocks execution.

## Audit payload

Every decision emits an audit payload with:

- policy snapshot
- top executable candidate id
- execution readiness candidate id
- safety contract version

## Current implementation

Implemented package:

```text
execution_safety/
  __init__.py
  contract.py
```

Implemented tests:

```text
tests/test_execution_safety.py
```

## Intentional limitation

No UI order button is added.
No broker adapter is added.
No execution endpoint is added.

That is intentional. The safety contract must be stable before any execution surface exists.

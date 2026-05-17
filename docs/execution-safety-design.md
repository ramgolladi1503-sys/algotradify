# Production Execution-Safety Design

This document defines the safety boundary before Algotradify can expose any execution controls.

## Hard rule

Execution safety design is not broker execution.

This layer must not:

- place orders
- call broker order APIs unless LIVE mode has passed the explicit broker-call guard
- modify orders
- cancel orders
- exit positions
- bypass execution readiness

## PR 51 execution-mode contract

Execution mode is now a first-class contract, not a loose string.

Supported modes:

```text
SIM
PAPER
LIVE
```

The default is `SIM`.

Mode contract implementation:

```text
execution_safety/contract.py
ExecutionMode
ExecutionModeContract
evaluate_execution_mode_contract
assert_broker_order_call_allowed
```

## Mode meanings

### SIM

Simulation mode allows simulated-order evidence only.

Hard guarantees:

- `simulated_order_allowed=true`
- `paper_order_allowed=false`
- `broker_api_allowed=false`
- `real_order_allowed=false`
- broker order guard raises before any broker placement can run

### PAPER

Paper mode allows paper-order evidence only.

Hard guarantees:

- `simulated_order_allowed=false`
- `paper_order_allowed=true`
- `broker_api_allowed=false`
- `real_order_allowed=false`
- broker order guard raises before any real broker placement can run

### LIVE

Live mode is blocked unless all LIVE readiness flags are explicit.

Required flags:

```text
real_broker_order_adapter_enabled=true
live_broker_ready=true
live_risk_ready=true
live_kill_switch_ready=true
```

Missing any flag blocks LIVE with one or more of:

```text
LIVE_REAL_BROKER_ADAPTER_NOT_ENABLED
LIVE_BROKER_READINESS_REQUIRED
LIVE_RISK_READINESS_REQUIRED
LIVE_KILL_SWITCH_READINESS_REQUIRED
```

Only after those flags pass can `broker_api_allowed=true` and `real_order_allowed=true` appear in the mode decision.

## Required gates before execution is permitted

1. Valid execution mode contract must pass.
2. Top executable candidate must exist.
3. Execution readiness must be allowed.
4. Manual approval must exist when required.
5. Operator identity must exist when manual approval is required.
6. Broker confirmation must exist when required.
7. Dry-run requirement must be cleared explicitly.
8. Kill switch must be off.
9. Daily loss guard must not be breached.
10. Daily order-count guard must not be breached.
11. Quantity guard must not be breached.
12. Warnings must be acknowledged.

## Kill switch

When `kill_switch_enabled=true`, execution is blocked regardless of all other evidence.

LIVE mode additionally requires `live_kill_switch_ready=true`, which means the production kill-switch mechanism itself has been explicitly confirmed ready before broker calls are allowed.

## Approval model

Manual approval requires:

- `approval_id`
- `operator_id`

Missing either blocks execution.

## Broker confirmation gate

When broker confirmation is required, `broker_confirmation_id` must be present. This prevents confusing selected candidates with confirmed broker-side readiness.

This is separate from `live_broker_ready=true`. Broker confirmation proves operator-visible confirmation. LIVE broker readiness proves the production broker adapter and account state are ready.

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
- execution mode contract snapshot
- execution mode decision snapshot
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
No real execution endpoint is added.

That is intentional. The safety contract must be stable before any execution surface exists.

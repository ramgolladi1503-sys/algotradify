# Paper Broker Order Lifecycle

PR 80 adds a paper-only order lifecycle contract.

## Why this exists

PR 79 created `PAPER_ORDER_INTENT` safely. PR 80 models lifecycle state transitions for that intent without real broker calls.

This is still not a fill simulator, PnL engine, UI, or LIVE adapter.

## Module

```text
paper_trading/lifecycle.py
```

## Public exports

```python
PaperOrderLifecycleEvent
PaperOrderLifecycleResult
PaperOrderLifecycleStatus
build_paper_order_lifecycle_event
paper_order_lifecycle_schema_contract
validate_paper_order_lifecycle_transition
```

## Lifecycle type

```text
PAPER_ORDER_LIFECYCLE
```

## Event type

```text
PAPER_ORDER_LIFECYCLE_EVENT
```

## Required safe flags

Every result and event returns:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## States

```text
CREATED
ACCEPTED
OPEN
PARTIALLY_FILLED
FILLED
REJECTED
CANCELLED
EXPIRED
```

## Terminal states

```text
FILLED
REJECTED
CANCELLED
EXPIRED
```

## Transition rules

```text
NONE -> CREATED
CREATED -> ACCEPTED | REJECTED | CANCELLED | EXPIRED
ACCEPTED -> OPEN | REJECTED | CANCELLED | EXPIRED
OPEN -> PARTIALLY_FILLED | FILLED | CANCELLED | EXPIRED | REJECTED
PARTIALLY_FILLED -> PARTIALLY_FILLED | FILLED | CANCELLED | EXPIRED
FILLED -> terminal
REJECTED -> terminal
CANCELLED -> terminal
EXPIRED -> terminal
```

## Validation blockers

```text
INVALID_PAPER_ORDER_STATUS
PAPER_INTENT_REQUIRED
PAPER_INTENT_NOT_PAPER_ONLY
PAPER_INTENT_ORDER_FLAG_UNSAFE
PAPER_INTENT_BROKER_API_CALLED
PAPER_INTENT_REAL_ORDER_ID_PRESENT
PAPER_ORDER_INTENT_ID_REQUIRED
CANDIDATE_ID_REQUIRED
UNKNOWN_PREVIOUS_PAPER_ORDER_STATUS
INVALID_PAPER_ORDER_TRANSITION
PAPER_ORDER_QUANTITY_REQUIRED_FOR_FILL
FILLED_QUANTITY_REQUIRED
FILLED_QUANTITY_MUST_BE_POSITIVE
FILLED_QUANTITY_EXCEEDS_ORDER_QUANTITY
PARTIAL_FILL_MUST_BE_LESS_THAN_ORDER_QUANTITY
```

## Test coverage

`tests/test_dry_run_execution_adapter.py` covers:

```text
schema contract safe flags
initial CREATED event
CREATED -> ACCEPTED flow
CREATED -> REJECTED flow
OPEN -> FILLED flow
OPEN -> PARTIALLY_FILLED -> CANCELLED flow
OPEN -> EXPIRED flow
invalid transition from terminal state
unsafe intent flags
bad fill quantities
safe flags on result and event
```

## Scope boundary

This PR does not add real broker execution, LIVE orders, UI rendering, fill simulation engine, slippage model, PnL, persistence, or replay analytics. It only models paper order lifecycle events.

## Next logical PR

```text
PR 81 — Paper Fill Simulation Engine
```

That PR should simulate fills against controlled quote/price inputs after lifecycle states are stable.

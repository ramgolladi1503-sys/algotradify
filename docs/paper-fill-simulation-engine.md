# Paper Fill Simulation Engine

PR 81 adds a paper-only fill simulation engine.

## Why this exists

PR 79 created `PAPER_ORDER_INTENT` safely.

PR 80 modeled `PAPER_ORDER_LIFECYCLE_EVENT` transitions safely.

PR 81 simulates fills from controlled quote/price inputs only. It does not use broker quotes, place orders, calculate PnL, model slippage, or touch UI.

## Module

```text
paper_trading/fill_simulation.py
```

## Public exports

```python
PaperFillSimulationResult
PaperFillSimulationStatus
paper_fill_simulation_schema_contract
simulate_paper_fill
validate_paper_fill_simulation_inputs
```

## Simulation type

```text
PAPER_FILL_SIMULATION_ENGINE
```

## Consumed contracts

```text
PAPER_ORDER_INTENT
PAPER_ORDER_LIFECYCLE_EVENT
CONTROLLED_QUOTE
```

## Required safe flags

Every result returns:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

Lifecycle events produced by the simulator also retain:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Supported simulation statuses

```text
FULL_FILL
PARTIAL_FILL
NO_FILL
REJECTED_FILL
EXPIRED_FILL
BLOCKED
```

## Controlled quote sources

The simulator only accepts quotes with one of these explicit sources:

```text
CONTROLLED_QUOTE
TEST_QUOTE
SIMULATED_QUOTE
PAPER_QUOTE
```

Any live/broker quote source is blocked.

## Fill rules

The simulator only runs when the previous lifecycle state is:

```text
OPEN
PARTIALLY_FILLED
```

For BUY orders:

```text
ask <= limit price -> fillable
ask > limit price  -> no fill
```

For SELL orders:

```text
bid >= limit price -> fillable
bid < limit price  -> no fill
```

Market orders use the executable controlled quote price directly.

Controlled quote liquidity is read from:

```text
available_quantity
available_qty
fillable_quantity
fillable_qty
size
quantity
```

If no liquidity field exists, remaining order quantity is assumed fillable.

## Lifecycle events created

```text
FULL_FILL      -> PAPER_ORDER_LIFECYCLE_EVENT status FILLED
PARTIAL_FILL   -> PAPER_ORDER_LIFECYCLE_EVENT status PARTIALLY_FILLED
REJECTED_FILL  -> PAPER_ORDER_LIFECYCLE_EVENT status REJECTED
EXPIRED_FILL   -> PAPER_ORDER_LIFECYCLE_EVENT status EXPIRED
NO_FILL        -> no lifecycle event
BLOCKED        -> no lifecycle event
```

The simulator calls the existing lifecycle builder instead of bypassing it. That means PR 80's transition rules remain the single source of truth.

## Validation blockers

```text
PAPER_INTENT_REQUIRED
PAPER_INTENT_TYPE_REQUIRED
PAPER_INTENT_NOT_PAPER_ONLY
PAPER_INTENT_ORDER_FLAG_UNSAFE
PAPER_INTENT_BROKER_API_CALLED
PAPER_INTENT_REAL_ORDER_ID_PRESENT
PAPER_ORDER_QUANTITY_REQUIRED
PAPER_ORDER_LIFECYCLE_EVENT_REQUIRED
PAPER_ORDER_LIFECYCLE_EVENT_TYPE_REQUIRED
PAPER_ORDER_LIFECYCLE_NOT_PAPER_ONLY
PAPER_ORDER_LIFECYCLE_ORDER_FLAG_UNSAFE
PAPER_ORDER_LIFECYCLE_BROKER_API_CALLED
PAPER_ORDER_LIFECYCLE_REAL_ORDER_ID_PRESENT
PAPER_ORDER_ALREADY_TERMINAL
PAPER_ORDER_NOT_OPEN_FOR_FILL_SIMULATION
PAPER_INTENT_LIFECYCLE_MISMATCH
PAPER_CANDIDATE_LIFECYCLE_MISMATCH
CONTROLLED_QUOTE_REQUIRED
CONTROLLED_QUOTE_SOURCE_REQUIRED
CONTROLLED_QUOTE_ORDER_FLAG_UNSAFE
CONTROLLED_QUOTE_BROKER_API_CALLED
CONTROLLED_QUOTE_REAL_ORDER_ID_PRESENT
CONTROLLED_QUOTE_STALE
```

## Test coverage

`tests/test_paper_fill_simulation.py` covers:

```text
schema contract safe flags
full fill from controlled quote
partial fill from controlled liquidity
no fill when limit is not marketable
rejected fill from controlled input
expired fill from controlled input
stale quote block
unsafe intent block
non-controlled quote source block
order-not-open block
safe flags on result and lifecycle event
```

## Scope boundary

This PR does not add:

```text
real broker execution
LIVE orders
broker quote consumption
UI changes
PnL tracking
slippage tracking
persistence
replay analytics
```

## Brutal note

This is intentionally boring and strict. If the simulator accepts live/broker data or emits anything that looks like a real order action, the abstraction is broken. Paper fills are useful only if they stay fake, controlled, and auditable.

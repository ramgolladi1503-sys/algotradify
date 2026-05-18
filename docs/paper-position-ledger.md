# Paper Position Ledger

PR 82 adds a paper-only position ledger.

## Why this exists

PR 79 created safe `PAPER_ORDER_INTENT` payloads.

PR 80 modeled safe `PAPER_ORDER_LIFECYCLE_EVENT` transitions.

PR 81 simulated paper fills from controlled quote inputs.

PR 82 turns fill lifecycle events into auditable paper positions without touching broker APIs, LIVE orders, PnL, slippage, or UI.

## Module

```text
paper_trading/position_ledger.py
```

## Public exports

```python
PaperPositionLedgerResult
PaperPositionLedgerStatus
build_paper_position_ledger
paper_position_ledger_schema_contract
validate_paper_position_ledger_inputs
```

## Ledger type

```text
PAPER_POSITION_LEDGER
```

## Consumed contracts

```text
PAPER_ORDER_INTENT
PAPER_ORDER_LIFECYCLE_EVENT
```

Only these lifecycle statuses can update positions:

```text
PARTIALLY_FILLED
FILLED
```

Other lifecycle statuses are ignored safely with `NO_POSITION_CHANGE`.

## Required safe flags

Every result, ledger, and position returns:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Ledger shape

```text
schema_version
ledger_type
positions
order_fills
last_event
paper_only
is_order_action
broker_api_called
real_order_id
```

## Position shape

```text
position_id
position_key
candidate_id
symbol
tradingsymbol
instrument_token
strategy
net_quantity
side
average_entry_price
last_fill_price
last_update_epoch
paper_only
is_order_action
broker_api_called
real_order_id
```

## Supported statuses

```text
POSITION_OPENED
POSITION_INCREASED
POSITION_REDUCED
POSITION_CLOSED
POSITION_REVERSED
NO_POSITION_CHANGE
BLOCKED
```

## Idempotency rule

Lifecycle fill quantities are cumulative per paper order.

The ledger stores:

```text
order_fills[paper_order_id] = cumulative_filled_quantity
```

For every new event, it applies only:

```text
delta_quantity = event.filled_quantity - previous_order_filled_quantity
```

This prevents duplicate partial-fill events from double-counting the position.

## Position side logic

```text
net_quantity > 0 -> LONG
net_quantity < 0 -> SHORT
net_quantity = 0 -> FLAT
```

BUY fills increase signed quantity.

SELL fills reduce signed quantity.

If a SELL quantity is larger than an existing LONG position, the position reverses to SHORT.

If a BUY quantity is larger than an existing SHORT position, the position reverses to LONG.

## Average price rule

The ledger tracks `average_entry_price` for position state only.

It does not calculate realized PnL.

It does not calculate slippage.

Rules:

```text
open new position -> fill price
increase same-side position -> weighted average
reduce existing position -> keep existing average
close position -> average_entry_price=null
reverse position -> fill price of reversing event
```

## Validation blockers

```text
PAPER_INTENT_REQUIRED
PAPER_INTENT_TYPE_REQUIRED
PAPER_INTENT_NOT_PAPER_ONLY
PAPER_INTENT_ORDER_FLAG_UNSAFE
PAPER_INTENT_BROKER_API_CALLED
PAPER_INTENT_REAL_ORDER_ID_PRESENT
PAPER_ORDER_QUANTITY_REQUIRED
PAPER_TRANSACTION_TYPE_REQUIRED
PAPER_ORDER_LIFECYCLE_EVENT_REQUIRED
PAPER_ORDER_LIFECYCLE_EVENT_TYPE_REQUIRED
PAPER_ORDER_LIFECYCLE_NOT_PAPER_ONLY
PAPER_ORDER_LIFECYCLE_ORDER_FLAG_UNSAFE
PAPER_ORDER_LIFECYCLE_BROKER_API_CALLED
PAPER_ORDER_LIFECYCLE_REAL_ORDER_ID_PRESENT
PAPER_ORDER_ID_REQUIRED
PAPER_FILLED_QUANTITY_INVALID
PAPER_INTENT_LIFECYCLE_MISMATCH
PAPER_CANDIDATE_LIFECYCLE_MISMATCH
PAPER_POSITION_LEDGER_TYPE_REQUIRED
PAPER_POSITION_LEDGER_NOT_PAPER_ONLY
PAPER_POSITION_LEDGER_ORDER_FLAG_UNSAFE
PAPER_POSITION_LEDGER_BROKER_API_CALLED
PAPER_POSITION_LEDGER_REAL_ORDER_ID_PRESENT
PAPER_POSITION_LEDGER_POSITIONS_INVALID
PAPER_POSITION_LEDGER_ORDER_FILLS_INVALID
PAPER_FILL_CUMULATIVE_REGRESSION
```

## Test coverage

`tests/test_paper_position_ledger.py` covers:

```text
schema contract safe flags
open long position from full BUY fill
incremental cumulative partial fill handling
duplicate fill idempotency
reduce position with SELL fill
close position without PnL
reverse position without real order IDs
ignore non-fill lifecycle events
block unsafe intent flags
block unsafe lifecycle event flags
block cumulative fill regression
```

## Scope boundary

This PR does not add:

```text
real broker execution
LIVE orders
PnL tracking
slippage tracking
UI changes
persistence
replay analytics
```

## Brutal note

Do not add PnL here. A ledger that cannot safely and idempotently answer “what paper position do I hold?” has no business calculating profitability yet.

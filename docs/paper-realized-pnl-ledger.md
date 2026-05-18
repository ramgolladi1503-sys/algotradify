# Paper Realized PnL Ledger

PR 84 adds a paper-only realized PnL ledger.

## Why this exists

PR 79 created safe `PAPER_ORDER_INTENT` payloads.

PR 80 modeled safe `PAPER_ORDER_LIFECYCLE_EVENT` transitions.

PR 81 simulated paper fills from controlled quote inputs.

PR 82 turned fills into an auditable `PAPER_POSITION_LEDGER`.

PR 83 calculated unrealized MTM from controlled marks.

PR 84 calculates realized PnL only when a fill reduces, closes, or reverses existing paper exposure.

## Module

```text
paper_trading/realized_pnl.py
```

## Public exports

```python
PaperRealizedPnlResult
PaperRealizedPnlStatus
build_paper_realized_pnl
paper_realized_pnl_schema_contract
validate_paper_realized_pnl_inputs
```

## Ledger type

```text
PAPER_REALIZED_PNL_LEDGER
```

## Consumed contracts

```text
PAPER_POSITION_LEDGER
PAPER_ORDER_INTENT
PAPER_ORDER_LIFECYCLE_EVENT
```

Important: this consumes the **previous** position ledger, before the reducing or closing fill is applied. That is required because realized PnL must use the prior position's average entry price and net quantity.

## Required safe flags

Every result, ledger, summary, and realized event returns:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Supported statuses

```text
REALIZED
NO_REALIZED_CHANGE
EMPTY
BLOCKED
```

## Fill event statuses

Only these lifecycle events can create realized PnL:

```text
PARTIALLY_FILLED
FILLED
```

Non-fill lifecycle events are ignored safely.

## Realized PnL formulas

For reducing or closing a LONG position:

```text
realized_pnl = (exit_price - average_entry_price) * realized_quantity
```

For reducing or closing a SHORT position:

```text
realized_pnl = (average_entry_price - exit_price) * realized_quantity
```

For reversals, only the quantity that closes the previous position is realized. The new opposite-side exposure is not realized in the same event.

## Idempotency rule

Fill lifecycle quantities are cumulative per paper order.

The ledger stores applied fill keys:

```text
fill_key = paper_order_id:cumulative_filled_quantity
```

A repeated fill key is ignored with:

```text
NO_REALIZED_CHANGE
DUPLICATE_REALIZED_PNL_FILL_KEY
```

Same-side fills that do not reduce exposure are also marked as applied so they cannot become duplicate accounting noise later.

## Ledger shape

```text
schema_version
ledger_type
events
applied_fill_keys
summary
paper_only
is_order_action
broker_api_called
real_order_id
```

## Realized event shape

```text
schema_version
event_type
realized_event_id
fill_key
paper_order_id
paper_order_intent_id
candidate_id
position_key
symbol
tradingsymbol
instrument_token
strategy
transaction_type
previous_net_quantity
signed_delta_quantity
realized_quantity
average_entry_price
exit_price
realized_pnl
ts_epoch
paper_only
is_order_action
broker_api_called
real_order_id
```

## Summary shape

```text
event_count
winning_event_count
losing_event_count
flat_event_count
total_realized_pnl
total_realized_quantity
paper_only
is_order_action
broker_api_called
real_order_id
```

## Validation blockers

```text
PREVIOUS_PAPER_POSITION_LEDGER_REQUIRED
PREVIOUS_PAPER_POSITION_LEDGER_TYPE_REQUIRED
PREVIOUS_PAPER_POSITION_LEDGER_NOT_PAPER_ONLY
PREVIOUS_PAPER_POSITION_LEDGER_ORDER_FLAG_UNSAFE
PREVIOUS_PAPER_POSITION_LEDGER_BROKER_API_CALLED
PREVIOUS_PAPER_POSITION_LEDGER_REAL_ORDER_ID_PRESENT
PREVIOUS_PAPER_POSITION_LEDGER_POSITIONS_INVALID
PREVIOUS_PAPER_POSITION_LEDGER_ORDER_FILLS_INVALID
PAPER_INTENT_REQUIRED
PAPER_INTENT_TYPE_REQUIRED
PAPER_INTENT_NOT_PAPER_ONLY
PAPER_INTENT_ORDER_FLAG_UNSAFE
PAPER_INTENT_BROKER_API_CALLED
PAPER_INTENT_REAL_ORDER_ID_PRESENT
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
PAPER_REALIZED_PNL_LEDGER_TYPE_REQUIRED
PAPER_REALIZED_PNL_LEDGER_NOT_PAPER_ONLY
PAPER_REALIZED_PNL_LEDGER_ORDER_FLAG_UNSAFE
PAPER_REALIZED_PNL_LEDGER_BROKER_API_CALLED
PAPER_REALIZED_PNL_LEDGER_REAL_ORDER_ID_PRESENT
PAPER_REALIZED_PNL_EVENTS_INVALID
PAPER_REALIZED_PNL_APPLIED_KEYS_INVALID
PAPER_FILL_CUMULATIVE_REGRESSION
REALIZED_PNL_PRICE_INPUT_REQUIRED
```

## Test coverage

`tests/test_paper_realized_pnl.py` covers:

```text
schema contract safe flags
partial close of LONG position
full close of SHORT position
reversal realizes only closed quantity
same-side fill creates no realized PnL
duplicate fill-key idempotency
non-fill lifecycle event ignored
missing price input block
unsafe previous position ledger flags block
unsafe lifecycle event flags block
cumulative fill regression block
```

## Scope boundary

This PR does not add:

```text
fees
slippage tracking
broker execution
LIVE orders
broker mark consumption
UI changes
persistence
replay analytics
```

## Brutal note

Realized PnL must use the previous position state. If you calculate it after mutating the position ledger, you are already late and probably wrong.

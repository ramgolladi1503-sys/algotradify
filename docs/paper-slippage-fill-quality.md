# Paper Slippage / Fill Quality Tracker

PR 85 adds a paper-only slippage and fill-quality evidence report.

## Why this exists

PR 79 created safe `PAPER_ORDER_INTENT` payloads.

PR 80 modeled safe `PAPER_ORDER_LIFECYCLE_EVENT` transitions.

PR 81 simulated paper fills from controlled quote inputs.

PR 82 turned fills into an auditable `PAPER_POSITION_LEDGER`.

PR 83 calculated unrealized MTM from controlled marks.

PR 84 calculated realized PnL from reducing/closing fills.

PR 85 measures fill quality by comparing expected paper price vs actual paper fill price.

## Module

```text
paper_trading/slippage.py
```

## Public exports

```python
PaperSlippageResult
PaperSlippageStatus
build_paper_slippage_report
paper_slippage_schema_contract
validate_paper_slippage_inputs
```

## Report type

```text
PAPER_SLIPPAGE_FILL_QUALITY
```

## Consumed contracts

```text
PAPER_ORDER_INTENT
PAPER_ORDER_LIFECYCLE_EVENT
CONTROLLED_EXPECTED_PRICE
```

## Required safe flags

Every result, report, summary, and slippage event returns:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Supported statuses

```text
MEASURED
NO_FILL
NO_SLIPPAGE_CHANGE
BLOCKED
```

## Fill event statuses

Only these lifecycle events can create slippage evidence:

```text
PARTIALLY_FILLED
FILLED
```

Non-fill lifecycle events are ignored safely.

## Slippage formulas

For BUY fills:

```text
slippage_per_unit = fill_price - expected_price
```

For SELL fills:

```text
slippage_per_unit = expected_price - fill_price
```

Then:

```text
slippage_amount = slippage_per_unit * measured_quantity
slippage_bps = (slippage_per_unit / expected_price) * 10000
```

Positive slippage means unfavorable fill quality.

Negative slippage means favorable fill quality.

Zero slippage means flat fill quality.

## Idempotency rule

Fill lifecycle quantities are cumulative per paper order.

The report stores:

```text
order_fills[paper_order_id] = cumulative_filled_quantity
fill_key = paper_order_id:cumulative_filled_quantity
```

For every new event, it applies only:

```text
measured_quantity = event.filled_quantity - previous_order_filled_quantity
```

This prevents duplicate partial-fill events from double-counting slippage.

## Expected price source

Expected price can be passed explicitly to `build_paper_slippage_report`.

If omitted, the tracker falls back to intent fields:

```text
expected_price
reference_price
price
entry_price
entry
```

## Report shape

```text
schema_version
report_type
events
applied_fill_keys
order_fills
summary
paper_only
is_order_action
broker_api_called
real_order_id
```

## Event shape

```text
schema_version
event_type
slippage_event_id
fill_key
paper_order_id
paper_order_intent_id
candidate_id
symbol
tradingsymbol
instrument_token
strategy
transaction_type
expected_price
fill_price
measured_quantity
slippage_per_unit
slippage_amount
slippage_bps
slippage_quality
ts_epoch
paper_only
is_order_action
broker_api_called
real_order_id
```

## Summary shape

```text
event_count
measured_quantity
total_slippage_amount
average_slippage_per_unit
weighted_average_slippage_bps
favorable_event_count
unfavorable_event_count
flat_event_count
paper_only
is_order_action
broker_api_called
real_order_id
```

## Validation blockers

```text
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
CONTROLLED_EXPECTED_PRICE_REQUIRED
PAPER_SLIPPAGE_REPORT_TYPE_REQUIRED
PAPER_SLIPPAGE_REPORT_NOT_PAPER_ONLY
PAPER_SLIPPAGE_REPORT_ORDER_FLAG_UNSAFE
PAPER_SLIPPAGE_REPORT_BROKER_API_CALLED
PAPER_SLIPPAGE_REPORT_REAL_ORDER_ID_PRESENT
PAPER_SLIPPAGE_EVENTS_INVALID
PAPER_SLIPPAGE_APPLIED_KEYS_INVALID
PAPER_SLIPPAGE_ORDER_FILLS_INVALID
PAPER_FILL_CUMULATIVE_REGRESSION
SLIPPAGE_PRICE_INPUT_REQUIRED
```

## Test coverage

`tests/test_paper_slippage.py` covers:

```text
schema contract safe flags
unfavorable BUY fill
favorable BUY fill
unfavorable SELL fill
incremental partial-fill slippage
duplicate fill-key idempotency
non-fill lifecycle event ignored
missing expected price block
missing fill price block
unsafe intent flags block
unsafe lifecycle event flags block
cumulative fill regression block
no PnL, fees, or broker fields in slippage event
```

## Scope boundary

This PR does not add:

```text
broker execution
LIVE orders
PnL mutation
fees
UI changes
persistence
replay analytics
```

## Brutal note

Slippage is fill-quality evidence, not a permission system. Do not let this layer start approving, blocking, or placing trades. That would mix analytics with execution and make the paper boundary dirty.

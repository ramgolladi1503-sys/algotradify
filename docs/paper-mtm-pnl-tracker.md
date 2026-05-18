# Paper MTM / Unrealized PnL Tracker

PR 83 adds a paper-only mark-to-market tracker for open paper positions.

## Why this exists

PR 79 created safe `PAPER_ORDER_INTENT` payloads.

PR 80 modeled safe `PAPER_ORDER_LIFECYCLE_EVENT` transitions.

PR 81 simulated paper fills from controlled quote inputs.

PR 82 turned fill events into an auditable `PAPER_POSITION_LEDGER`.

PR 83 values open paper positions from controlled mark inputs only.

## Module

```text
paper_trading/mtm_pnl.py
```

## Public exports

```python
PaperMtmPnlResult
PaperMtmPnlStatus
build_paper_mtm_pnl
paper_mtm_pnl_schema_contract
validate_paper_mtm_pnl_inputs
```

## Tracker type

```text
PAPER_MTM_PNL_TRACKER
```

## Consumed contracts

```text
PAPER_POSITION_LEDGER
CONTROLLED_MARK
```

## Required safe flags

Every result, row, and summary returns:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Controlled mark sources

Allowed mark sources only:

```text
CONTROLLED_MARK
TEST_MARK
SIMULATED_MARK
PAPER_MARK
```

Live/broker mark sources are blocked.

## Supported statuses

```text
VALUED
DEGRADED_MISSING_MARK
EMPTY
BLOCKED
```

## Row shape

```text
position_id
position_key
symbol
tradingsymbol
instrument_token
strategy
net_quantity
side
average_entry_price
mark_price
unrealized_pnl
notional_value
row_status
paper_only
is_order_action
broker_api_called
real_order_id
```

## Summary shape

```text
position_count
open_position_count
valued_position_count
missing_mark_count
total_unrealized_pnl
gross_notional_value
net_quantity_abs
paper_only
is_order_action
broker_api_called
real_order_id
```

## MTM formula

For LONG positions:

```text
unrealized_pnl = (mark_price - average_entry_price) * abs(net_quantity)
```

For SHORT positions:

```text
unrealized_pnl = (average_entry_price - mark_price) * abs(net_quantity)
```

Flat positions are valued as zero unrealized PnL and zero notional.

## Degraded valuation

If an open position is missing a mark price, the tracker returns:

```text
status=DEGRADED_MISSING_MARK
valued=false
```

Rows with missing marks return:

```text
row_status=MISSING_MARK
unrealized_pnl=null
notional_value=null
```

## Validation blockers

```text
PAPER_POSITION_LEDGER_REQUIRED
PAPER_POSITION_LEDGER_TYPE_REQUIRED
PAPER_POSITION_LEDGER_NOT_PAPER_ONLY
PAPER_POSITION_LEDGER_ORDER_FLAG_UNSAFE
PAPER_POSITION_LEDGER_BROKER_API_CALLED
PAPER_POSITION_LEDGER_REAL_ORDER_ID_PRESENT
PAPER_POSITION_LEDGER_POSITIONS_INVALID
CONTROLLED_MARK_REQUIRED
CONTROLLED_MARK_SOURCE_REQUIRED
CONTROLLED_MARK_ORDER_FLAG_UNSAFE
CONTROLLED_MARK_BROKER_API_CALLED
CONTROLLED_MARK_REAL_ORDER_ID_PRESENT
CONTROLLED_MARK_STALE
CONTROLLED_MARKS_MAP_INVALID
CONTROLLED_MARK_ROW_ORDER_FLAG_UNSAFE:<key>
CONTROLLED_MARK_ROW_BROKER_API_CALLED:<key>
CONTROLLED_MARK_ROW_REAL_ORDER_ID_PRESENT:<key>
CONTROLLED_MARK_ROW_STALE:<key>
```

## Test coverage

`tests/test_paper_mtm_pnl.py` covers:

```text
schema contract safe flags
LONG MTM valuation
SHORT MTM valuation
missing mark degradation
flat position zero valuation
stale controlled mark block
non-controlled mark source block
unsafe ledger flags block
unsafe mark flags block
unsafe nested mark row block
empty ledger safe state
no realized PnL, fees, or slippage fields
```

## Scope boundary

This PR does not add:

```text
realized PnL
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

This tracker is intentionally only unrealized MTM. Realized PnL needs complete close/reduce event accounting. Adding it here would be fake precision and would make the paper system less trustworthy.

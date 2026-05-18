# Paper Performance Snapshot

PR 86 adds a paper-only, read-only performance snapshot.

## Why this exists

The paper chain now has separate evidence contracts:

```text
PAPER_POSITION_LEDGER
PAPER_MTM_PNL_TRACKER
PAPER_REALIZED_PNL_LEDGER
PAPER_SLIPPAGE_FILL_QUALITY
```

PR 86 aggregates those contracts into one safe snapshot for later API/UI work.

This PR does not add UI, persistence, replay analytics, order decisions, or execution behavior.

## Module

```text
paper_trading/performance_snapshot.py
```

## Public exports

```python
PaperPerformanceSnapshotResult
PaperPerformanceSnapshotStatus
build_paper_performance_snapshot
paper_performance_snapshot_schema_contract
validate_paper_performance_snapshot_inputs
```

## Snapshot type

```text
PAPER_PERFORMANCE_SNAPSHOT
```

## Consumed contracts

```text
PAPER_POSITION_LEDGER
PAPER_MTM_PNL_TRACKER
PAPER_REALIZED_PNL_LEDGER
PAPER_SLIPPAGE_FILL_QUALITY
```

Only `PAPER_POSITION_LEDGER` is required. MTM, realized PnL, and slippage are optional sources. If optional sources are missing, the snapshot is created as degraded.

## Required safe flags

Every result and nested block returns:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Supported statuses

```text
READY
DEGRADED
EMPTY
BLOCKED
```

## Snapshot shape

```text
schema_version
snapshot_type
status
ts_epoch
summary
positions
pnl
slippage
diagnostics
source_statuses
paper_only
read_only
is_order_action
broker_api_called
real_order_id
```

## Summary shape

```text
position_count
open_position_count
net_quantity_abs
total_unrealized_pnl
total_realized_pnl
combined_pnl
gross_notional_value
slippage_event_count
total_slippage_amount
paper_only
read_only
is_order_action
broker_api_called
real_order_id
```

## Position aggregation

The snapshot summarizes:

```text
position_count
open_position_count
long_position_count
short_position_count
flat_position_count
net_quantity_abs
positions
```

It does not mutate positions.

## PnL aggregation

The snapshot summarizes:

```text
total_unrealized_pnl
total_realized_pnl
combined_pnl
gross_notional_value
valued_position_count
missing_mark_count
realized_event_count
winning_event_count
losing_event_count
```

`combined_pnl` is:

```text
total_unrealized_pnl + total_realized_pnl
```

## Slippage aggregation

The snapshot summarizes:

```text
slippage_event_count
measured_quantity
total_slippage_amount
average_slippage_per_unit
weighted_average_slippage_bps
favorable_event_count
unfavorable_event_count
flat_event_count
```

## Diagnostics

Diagnostics include:

```text
missing_sources
degraded_sources
warning_count
position_source_present
```

Missing optional sources degrade the snapshot instead of blocking it.

## Blocking conditions

```text
PAPER_POSITION_LEDGER_REQUIRED
PAPER_POSITION_LEDGER_TYPE_REQUIRED
PAPER_POSITION_LEDGER_NOT_PAPER_ONLY
PAPER_POSITION_LEDGER_ORDER_FLAG_UNSAFE
PAPER_POSITION_LEDGER_BROKER_API_CALLED
PAPER_POSITION_LEDGER_REAL_ORDER_ID_PRESENT
PAPER_POSITION_LEDGER_POSITIONS_INVALID
PAPER_MTM_PNL_TRACKER_TYPE_REQUIRED
PAPER_MTM_PNL_TRACKER_NOT_PAPER_ONLY
PAPER_MTM_PNL_TRACKER_ORDER_FLAG_UNSAFE
PAPER_MTM_PNL_TRACKER_BROKER_API_CALLED
PAPER_MTM_PNL_TRACKER_REAL_ORDER_ID_PRESENT
PAPER_REALIZED_PNL_LEDGER_TYPE_REQUIRED
PAPER_REALIZED_PNL_LEDGER_NOT_PAPER_ONLY
PAPER_REALIZED_PNL_LEDGER_ORDER_FLAG_UNSAFE
PAPER_REALIZED_PNL_LEDGER_BROKER_API_CALLED
PAPER_REALIZED_PNL_LEDGER_REAL_ORDER_ID_PRESENT
PAPER_SLIPPAGE_FILL_QUALITY_TYPE_REQUIRED
PAPER_SLIPPAGE_FILL_QUALITY_NOT_PAPER_ONLY
PAPER_SLIPPAGE_FILL_QUALITY_ORDER_FLAG_UNSAFE
PAPER_SLIPPAGE_FILL_QUALITY_BROKER_API_CALLED
PAPER_SLIPPAGE_FILL_QUALITY_REAL_ORDER_ID_PRESENT
```

## Test coverage

`tests/test_paper_performance_snapshot.py` covers:

```text
schema contract safe flags
READY aggregation from all sources
DEGRADED when optional sources are missing
EMPTY when no positions or metrics exist
DEGRADED when MTM source is degraded
BLOCKED when position ledger is missing
BLOCKED on unsafe position ledger flags
BLOCKED on wrong optional source type
no submit/modify/cancel/exit/order controls
nested safe flags on every block
```

## Scope boundary

This PR does not add:

```text
broker execution
LIVE orders
UI rendering
persistence
replay analytics
order decisions
order controls
```

## Brutal note

This is aggregation only. If this layer starts deciding whether to trade, it becomes an execution gate. That would be a design bug.

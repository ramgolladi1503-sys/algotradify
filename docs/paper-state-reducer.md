# Deterministic Paper State Reducer

PR 88 adds the deterministic paper state reducer.

## Purpose

The reducer derives read-only paper state from canonical paper events.

```text
Journal is truth.
Reducer derives state.
Snapshots are outputs.
```

This reducer is intentionally pure. It does not read files, write files, call brokers, place orders, expose APIs, or render UI.

## Scope

This PR adds:

```text
paper_trading/state_reducer.py
tests/test_paper_state_reducer.py
docs/paper-state-reducer.md
```

It does not add:

```text
broker execution
LIVE orders
runtime wiring
API
dashboard/UI
state rebuild CLI
reconciliation report
full event ordering guard
journal persistence changes
```

## Reducer contract

Consumes:

```text
CANONICAL_PAPER_EVENT_JOURNAL
```

Produces:

```text
PAPER_REDUCED_STATE
```

The output state contains:

```text
orders
positions
pnl_marks
slippage_measurements
performance_snapshots
applied_event_ids
applied_idempotency_keys
last_event
summary
```

## Safety flags

The reducer result, state, summary, orders, positions, and analytics rows expose:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Behavior

The reducer applies canonical events in the order provided.

Order events update current paper order state:

```text
PAPER_ORDER_INTENT_CREATED -> INTENT_CREATED
PAPER_ORDER_ACCEPTED -> ACCEPTED
PAPER_ORDER_REJECTED -> REJECTED
PAPER_ORDER_OPENED -> OPEN
PAPER_ORDER_PARTIALLY_FILLED -> PARTIALLY_FILLED
PAPER_ORDER_FILLED -> FILLED
PAPER_ORDER_CANCELLED -> CANCELLED
PAPER_ORDER_EXPIRED -> EXPIRED
```

Position events update current paper position state:

```text
PAPER_POSITION_OPENED
PAPER_POSITION_INCREASED
PAPER_POSITION_REDUCED
PAPER_POSITION_CLOSED
PAPER_POSITION_REVERSED
```

Analytics events are stored as read-only evidence:

```text
PAPER_PNL_MARKED
PAPER_SLIPPAGE_MEASURED
PAPER_PERFORMANCE_SNAPSHOT_CREATED
```

## Block behavior

The reducer blocks unsafe or ambiguous input:

```text
missing event list
non-list event input
invalid canonical event
unsafe paper/order/broker flags
real_order_id present
duplicate event_id
duplicate idempotency_key
position event missing position key
position event missing net_quantity, except CLOSED
```

## Determinism

The reducer uses no clock, no randomness, no file system, no network, no hidden global state, and no broker imports.

Same input produces the same output.

## Important boundary

This PR does not enforce global ordering across event sequences or timestamps. That belongs to PR 89 — Paper Event Ordering and Idempotency Guard.

Do not add rebuild CLI behavior here. That belongs to PR 90.

Do not add reconciliation here. That belongs to PR 91.

## Validation

Focused validation:

```bash
python -m pytest tests/test_paper_state_reducer.py -q
```

Recommended adjacent validation:

```bash
python -m pytest tests/test_paper_event_journal.py -q
python -m pytest tests/test_paper_position_ledger.py -q
python -m pytest tests/test_paper_performance_snapshot.py -q
```

# Canonical Paper Event Journal

PR 87 introduces the append-only paper event journal. This is the first paper-truth foundation layer.

## Purpose

The journal is the source of truth for paper trading events. Reducers, snapshots, reconciliation reports, replay views, and later APIs must derive from this journal instead of treating snapshots as truth.

Blunt rule:

```text
Journal is truth. Reducer derives state. Snapshots are outputs.
```

## Scope

This PR adds only:

```text
paper_trading/events.py
paper_trading/event_journal.py
tests/test_paper_event_journal.py
```

It does not add:

```text
broker execution
LIVE orders
paper reducer
state rebuild CLI
reconciliation report
runtime wiring
API
dashboard/UI
order controls
```

## Canonical event fields

Every event must contain:

```text
schema_version
event_id
cycle_id
event_sequence
candidate_id
strategy_id
paper_order_intent_id
paper_order_id
event_type
ts_epoch
idempotency_key
payload
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Event types

```text
PAPER_ORDER_INTENT_CREATED
PAPER_ORDER_ACCEPTED
PAPER_ORDER_REJECTED
PAPER_ORDER_OPENED
PAPER_ORDER_PARTIALLY_FILLED
PAPER_ORDER_FILLED
PAPER_ORDER_CANCELLED
PAPER_ORDER_EXPIRED
PAPER_POSITION_OPENED
PAPER_POSITION_INCREASED
PAPER_POSITION_REDUCED
PAPER_POSITION_CLOSED
PAPER_POSITION_REVERSED
PAPER_PNL_MARKED
PAPER_SLIPPAGE_MEASURED
PAPER_PERFORMANCE_SNAPSHOT_CREATED
```

## Safety contract

The journal blocks events when:

```text
paper_only != true
is_order_action != false
broker_api_called != false
real_order_id is present
cycle_id is missing
event_type is missing or unsupported
ts_epoch is missing
payload is not an object
```

This module is paper-only and has no broker imports.

## Idempotency contract

```text
duplicate event_id -> blocked
same idempotency_key and same event -> deterministic no-op
same idempotency_key and different event -> blocked
```

The no-op behavior is intentional. It allows safe retry of the exact same append without mutating the journal.

## Storage format

The journal uses JSONL.

Each append writes exactly one stable JSON object followed by one newline. Existing lines are loaded and validated before append. If the existing journal contains corrupt JSONL or unsafe historical rows, append fails closed and does not mutate the file.

## Current limitation

This PR intentionally does not enforce global ordering across `event_sequence` or timestamps. That belongs to PR 89 — Paper Event Ordering and Idempotency Guard. Adding it here would mix scopes and create PR-loop risk.

## Validation

Run:

```bash
python -m pytest tests/test_paper_event_journal.py -q
```

Recommended adjacent checks:

```bash
python -m pytest tests/test_paper_performance_snapshot.py -q
python -m pytest tests/test_paper_slippage.py -q
python -m pytest tests/test_paper_position_ledger.py -q
```

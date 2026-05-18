# Paper Event Ordering and Idempotency Guard

PR 89 adds a read-only guard for canonical paper journal ordering and idempotency.

## Purpose

The paper journal is truth, but truth must be ordered and non-duplicated before rebuild and reconciliation can be trusted.

This guard validates the canonical paper event list before downstream reducers, rebuild CLI, reconciliation reports, or replay tooling use it.

## Scope

This PR adds:

```text
paper_trading/event_ordering.py
tests/test_paper_event_ordering.py
docs/paper-event-ordering-guard.md
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
reducer mutation
journal persistence mutation
```

## Contract

Consumes:

```text
CANONICAL_PAPER_EVENT_JOURNAL
```

Produces:

```text
PAPER_EVENT_ORDERING_IDEMPOTENCY_GUARD
```

The guard is read-only. It validates and returns the ordered events only when they already satisfy the invariants. It does not repair, sort, rewrite, or append events.

## Safety flags

The result and cycle summaries expose:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Rules

The guard blocks:

```text
missing event list
non-list event input
invalid canonical event
unsafe paper/order/broker flags
real_order_id present
duplicate event_id
duplicate idempotency_key
cycle event_sequence that does not start at 1
cycle event_sequence gap
cycle event_sequence regression
cycle ts_epoch regression
```

## Ordering policy

Events are validated in the order provided.

The guard deliberately does not sort events by sequence or timestamp. Silent sorting would hide journal corruption and create fake deterministic state.

Each cycle must satisfy:

```text
first event_sequence = 1
next event_sequence = previous event_sequence + 1
ts_epoch must be non-decreasing inside the same cycle
```

Different cycles are independent. Each cycle starts at sequence 1.

## Idempotency policy

```text
event_id must be globally unique
idempotency_key must be globally unique
```

Exact retry handling stays at the append layer from PR 87. By the time events reach this guard, duplicate idempotency keys mean the event list is not safe for deterministic reduction.

## Why fail closed?

Because downstream state rebuild and reconciliation will be worthless if the guard silently repairs bad input.

Bad example:

```text
sequence 1, sequence 3
```

The guard blocks it. It does not guess whether sequence 2 was dropped, skipped, or corrupted.

Bad example:

```text
sequence 2, sequence 1
```

The guard blocks it. It does not sort the events and pretend the journal was clean.

## Validation

Focused validation:

```bash
python -m pytest tests/test_paper_event_ordering.py -q
```

Recommended adjacent validation:

```bash
python -m pytest tests/test_paper_event_journal.py -q
python -m pytest tests/test_paper_state_reducer.py -q
```

## Next PR boundary

PR 90 may use this guard before rebuilding state from a persisted journal.

Do not add rebuild CLI behavior here.

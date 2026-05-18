# Paper State Rebuild CLI

PR 90 adds a read-only rebuild path for canonical paper journals.

## Purpose

Paper state must be derived from the canonical event journal, not from snapshots or mutable runtime state.

This layer proves that a persisted paper journal can be rebuilt deterministically into derived state.

## Pipeline

```text
load_paper_events
  -> guard_paper_event_ordering
  -> reduce_paper_events
```

The rebuild path does not sort, repair, append, export, or mutate the journal.

## CLI

```bash
python scripts/rebuild_paper_journal.py --journal runtime/paper/events.jsonl
python scripts/rebuild_paper_journal.py --journal runtime/paper/events.jsonl --json
```

## Statuses

```text
REBUILT
EMPTY
BLOCKED
```

`REBUILT` means the journal loaded, ordering/idempotency checks passed, and the reducer derived state.

`EMPTY` means the journal path is valid but there are no events to rebuild. This is safe for a new paper session.

`BLOCKED` means the rebuild contract failed. Corrupt JSONL, unsafe historical events, duplicate event IDs, duplicate idempotency keys, sequence gaps, timestamp regressions, and reducer blockers fail closed.

## Exit codes

```text
REBUILT -> 0
EMPTY   -> 0
BLOCKED -> 2
```

## Safety contract

Every rebuild result exposes:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Scope boundary

This PR does not add:

```text
broker execution
LIVE orders
API endpoint
UI/dashboard
runtime wiring
journal append changes
state export files
reconciliation report
strategy/provider work
ML/ranker work
```

## Acceptance proof

Focused:

```bash
python -m pytest tests/test_paper_journal_rebuild.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_event_journal.py tests/test_paper_event_ordering.py tests/test_paper_state_reducer.py -q
```

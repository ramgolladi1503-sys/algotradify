# Paper State Reconciliation Report

PR 91 adds a read-only reconciliation report for paper state.

## Purpose

PR 90 proved that paper state can be rebuilt from the canonical journal.

PR 91 checks whether that rebuilt state agrees with an observed/current paper state snapshot.

This is not a new source of truth. The journal remains truth. The reducer derives state. Reconciliation only reports whether observed state drifted from rebuilt truth.

## Pipeline

```text
canonical journal
  -> rebuild_paper_journal
  -> rebuilt_state
  -> reconcile_paper_state(rebuilt_state, observed_state)
  -> MATCH / DRIFT / EMPTY / BLOCKED
```

## Statuses

```text
MATCH
DRIFT
EMPTY
BLOCKED
```

`MATCH` means rebuilt and observed state agree across compared fields.

`DRIFT` means both inputs are valid, but differences exist.

`EMPTY` means rebuilt state is empty and no observed state exists or observed state is also empty.

`BLOCKED` means the reconciliation input is unsafe or invalid.

## Compared fields

```text
orders
positions
summary
applied_event_ids
applied_idempotency_keys
last_event
```

## Blocking conditions

```text
missing rebuild result
blocked rebuild result
missing rebuilt state
unsafe rebuilt state flags
unsafe observed state flags
missing required state keys
non-object observed state
non-object rebuild result
```

## CLI

```bash
python scripts/reconcile_paper_state.py --journal runtime/paper/events.jsonl --json
python scripts/reconcile_paper_state.py --journal runtime/paper/events.jsonl --observed-state runtime/paper/observed-state.json --json
```

The observed state file may be either a raw state object or an object containing a `state` object.

## Exit codes

```text
MATCH   -> 0
EMPTY   -> 0
DRIFT   -> 1
BLOCKED -> 2
```

## Safety contract

Every reconciliation report exposes:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

Each drift row also preserves the same safe flags.

## Scope boundary

This PR does not add:

```text
journal mutation
observed state persistence
paper orchestrator
API endpoint
UI/dashboard
runtime wiring
broker execution
LIVE orders
strategy/provider work
ML/ranker work
```

## Acceptance proof

Focused:

```bash
python -m pytest tests/test_paper_state_reconciliation.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_journal_rebuild.py tests/test_paper_event_journal.py tests/test_paper_event_ordering.py tests/test_paper_state_reducer.py -q
```

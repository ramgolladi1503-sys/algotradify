# Replay Result Drilldown UX

PR 43 improves the Control Tower replay view after PR 42 added replay timeline filters.

## Goal

Make filtered replay results easier to inspect without changing backend behavior.

The replay card now keeps the PR 42 filters and adds a structured drilldown for returned events.

## What the drilldown shows

The Control Tower groups replay events by:

```text
candidate_id
```

Each candidate group shows:

- event count
- strategy
- first timestamp
- last timestamp
- latest status pill
- status transition chain
- ordered event timeline
- raw event evidence under an expandable block

## Timeline ordering

Replay events are ordered by the first available timestamp field:

- `ts_epoch`
- `timestamp`
- `time`
- `created_at`

Events without parseable numeric time are pushed to the end.

## Status transition chain

The UI derives a compact chain from ordered events:

```text
SELECTED -> FILLED -> CLOSED
```

This is UI-only interpretation of existing replay records. It does not mutate replay data.

## Empty state

When filters return no rows, the card shows:

- no replay results match the active filters
- suggested fields to check: `candidate_id`, `status`, `strategy`, and time range
- active replay filters

## Safety boundary

This is a read-only Control Tower UX change.

It does not add:

- backend route behavior
- broker API calls
- real order placement
- order-management UI
- approval controls
- JSONL append behavior
- runtime mutation
- live or paper execution adapters

## Tests

Relevant test file:

```text
tests/test_control_tower_ui.py
```

New contract coverage verifies:

- result grouping by candidate
- timeline ordering helpers
- status transition chain rendering
- strategy and timestamp fields
- empty-state explanation
- no forbidden order-management labels
- no frontend append query literal

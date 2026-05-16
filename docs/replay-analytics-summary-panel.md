# Replay Analytics Summary Panel

PR 44 adds a read-only replay analytics summary panel to the Control Tower.

## Goal

Give operators a compact summary of the active replay result set before they inspect candidate drilldowns.

This builds on:

- PR 42: replay timeline filters
- PR 43: replay result drilldown UX

## Source data

The panel derives analytics from the already-filtered replay events in the frontend.

It does not require a new backend endpoint.

## Summary fields

The panel shows:

- `candidate_count`
- `event_count`
- `time_window_min`
- `time_window_max`
- `best_quality_score`
- `worst_quality_score`
- status distribution
- strategy distribution

## Time-window behavior

The panel reads the first available timestamp-like field from each event:

- `ts_epoch`
- `timestamp`
- `time`
- `created_at`

Only parseable numeric timestamps are used for min/max time-window metrics.

## Quality-score behavior

The panel reads the first available score-like field from each event:

- `quality_score`
- `trade_quality_score`
- `score`

Only numeric values are used for best/worst score metrics.

## Safety boundary

This is a frontend read-only analytics view.

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

Contract coverage verifies:

- panel title
- summary helper function names
- candidate/event counts
- status and strategy distributions
- min/max time-window fields
- best/worst quality-score fields
- read-only label
- absence of forbidden execution labels

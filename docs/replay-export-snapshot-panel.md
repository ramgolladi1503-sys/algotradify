# Replay Export Snapshot Panel

PR 45 adds a read-only replay export snapshot panel to the Control Tower.

## Goal

Give operators a copyable JSON snapshot of the currently filtered replay view.

This builds on:

- PR 42: replay timeline filters
- PR 43: replay result drilldown UX
- PR 44: replay analytics summary panel

## Source data

The snapshot is derived from the existing frontend state:

- active replay filters
- replay query metadata
- filtered replay events
- replay analytics summary
- grouped replay timeline

No new backend endpoint is required.

## Snapshot shape

The snapshot contains:

```json
{
  "snapshot_type": "control_tower_replay_export_snapshot",
  "read_only": true,
  "source": "frontend_filtered_replay_view",
  "filters": {},
  "query_metadata": {},
  "analytics_summary": {},
  "grouped_timeline": [],
  "events": []
}
```

## UI behavior

The panel renders a read-only textarea containing formatted JSON.

The user can manually copy the JSON from the page.

## Safety boundary

This is a frontend read-only snapshot view.

It does not add:

- backend route behavior
- broker API calls
- real order placement
- order-management UI
- approval controls
- JSONL append behavior
- runtime mutation
- live or paper execution adapters
- server-side file writes

## Tests

Relevant test file:

```text
tests/test_control_tower_ui.py
```

Contract coverage verifies:

- panel title
- snapshot builder function
- grouped timeline helper
- snapshot type
- filters and query metadata
- analytics summary
- grouped timeline
- copyable read-only JSON label
- read-only textarea
- absence of forbidden execution labels

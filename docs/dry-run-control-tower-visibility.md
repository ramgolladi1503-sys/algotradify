# Dry-Run Control Tower Visibility

PR 28 adds read-only dry-run execution evidence to the Control Tower.

## UI endpoint

The frontend calls:

```text
GET /dry-run-execution?limit=20
```

It does not call `append=true`.

## Displayed fields

The Control Tower card displays:

- `created`
- `dry_run_only`
- `is_order_action`
- `broker_api_called`
- `dry_run_order_id`
- `real_order_id`
- blockers
- warnings

## Safety boundary

The card is visibility-only. It does not create a mutation control, does not write artifacts, and does not provide live execution controls.

Allowed UI wording:

- Dry-Run Execution Adapter
- Preview Dry Run
- dry-run evidence

Forbidden UI behavior:

- calling `append=true`
- creating external execution controls
- adding submit/modify/cancel/exit controls

## Tests

`tests/test_control_tower_ui.py` verifies that the dry-run endpoint and card are present and that the frontend does not call `append=true`.

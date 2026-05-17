# Movement Opportunity Dashboard Read-only Panel

PR 70 adds a read-only Control Tower panel for the Movement Opportunity API contract locked in PR 69.

## Files

```text
frontend/movementOpportunityPanel.jsx
frontend/main.jsx
tests/test_movement_opportunity_panel_ui.py
.github/workflows/frontend-contract-ci.yml
docs/movement-opportunity-dashboard-panel.md
```

## UI behavior

The panel fetches:

```text
GET /movement-opportunity?symbol=<symbol>&ts_epoch=<timestamp>
```

Default query:

```text
symbol=NIFTY
ts_epoch=77777
```

The panel renders:

```text
Movement API safety flags
Movement summary
Movement ranked candidates
Movement rank records
Movement exclusions
Movement diagnostics
Raw movement opportunity payload
```

## Visible safe flags

The panel visibly checks:

```text
read_only
is_order_action
context.is_order_action
summary.read_only
summary.is_order_action
pipeline.read_only
pipeline.is_order_action
pipeline.rank_result.is_order_action
```

It also checks collection items:

```text
ranked_candidates[].is_order_action
rank_records[].is_order_action
exclusions[].is_order_action
diagnostics[].is_order_action
```

## Query controls

The panel exposes only query controls:

```text
movement symbol query
movement ts_epoch query
Apply movement opportunity query
Reset movement opportunity query
```

These controls only change the read-only API request.

## Control Tower integration

`frontend/main.jsx` now stores movement query preferences alongside existing Control Tower preferences and adds a Movement focus operator view.

## Contract tests

`tests/test_movement_opportunity_panel_ui.py` proves:

```text
panel component exists
panel is wired into Control Tower
frontend builds /movement-opportunity query string
panel renders PR 69 response sections
panel exposes read-only safe flags
panel has no write-style movement controls
movement query preferences persist with existing preferences
```

## CI

`frontend-contract-ci.yml` runs:

```bash
pytest -q tests/test_control_tower_ui.py tests/test_movement_opportunity_panel_ui.py
```

## Honest limitation

This PR is frontend-contract focused. The panel expects the API process to expose `/movement-opportunity`, either through the movement-enabled API adapter or an equivalent app mount. The main API mount should be verified before relying on the panel in a live demo.

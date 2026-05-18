# Movement Dashboard Fixture/Snapshot Contracts

PR 73 adds deterministic fixture and snapshot contracts for the Movement Opportunity Dashboard Read-only Panel.

## Why this exists

PR 70 added the movement dashboard panel.
PR 71 mounted the movement API on the main server.
PR 72 proved the route works through the Control Tower runtime path.

PR 73 locks the panel against deterministic fixture states so future UI edits cannot silently break expected movement dashboard behavior.

## Fixture files

```text
tests/fixtures/movement_opportunity/happy_ranked_candidate.json
tests/fixtures/movement_opportunity/empty_no_candidate.json
tests/fixtures/movement_opportunity/blocked_candidate.json
```

## Fixture states

### Happy ranked candidate

Represents a normal read-only movement response with one ranked candidate:

```text
ranked_count=1
blocked_count=0
excluded_count=0
top_candidate_id=move_nifty_opening_drive_001
read_only=true
is_order_action=false
```

### Empty no-candidate state

Represents a stable no-op dashboard state:

```text
ranked_count=0
blocked_count=0
excluded_count=0
diagnostic_codes=[NO_MOVEMENT_CANDIDATES]
read_only=true
is_order_action=false
```

### Blocked candidate state

Represents a stable blocked dashboard state:

```text
ranked_count=0
blocked_count=2
no_trade_count=2
excluded_count=2
diagnostic_codes=[ALL_MOVEMENT_CANDIDATES_BLOCKED]
read_only=true
is_order_action=false
```

## Test coverage

`tests/test_movement_opportunity_panel_ui.py` now validates:

```text
fixture files exist
fixtures keep PR 69 top-level response contract
fixtures keep public safe flags
happy snapshot remains stable
empty snapshot remains stable
blocked snapshot remains stable
panel source renders empty states
panel source renders blocked states
panel source renders ranked candidate columns
fixtures never claim is_order_action=true
fixtures never include broker/result order fields
```

## CI wiring

The tests were added to the existing movement panel UI contract test file:

```text
tests/test_movement_opportunity_panel_ui.py
```

That file is already run by Frontend Contract CI, so this is real coverage, not an unwired test island.

## Scope boundary

This PR does not add providers, UI features, runtime behavior, order behavior, or ranking logic. It only freezes deterministic dashboard fixture states.

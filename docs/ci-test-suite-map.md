# CI Test Suite Map

Algotradify uses focused GitHub Actions lanes instead of relying on one opaque test command.

## Lanes

### Portfolio CI

Broad repository gate. Validates required portfolio files, README sections, and the full curated test set.

Portfolio CI is the broadest safety net. It includes the replay contract chain so replay API, fixtures, and Control Tower UI contracts cannot drift silently.

### Core Unit CI

Runs pure backend unit tests for:

- runtime contract
- runtime preflight
- strategy registry
- candidate truth
- opportunity layer
- broker contract resolver/readiness
- market readiness
- execution readiness
- evidence wiring
- trade quality
- top executable selector

### Lifecycle and Safety CI

Runs lifecycle and safety tests for:

- fill lifecycle
- outcome replay
- execution safety
- approval audit
- approval creation

### API Contract CI

Runs endpoint, schema, and websocket contract tests.

Replay API behavior is additionally protected by the replay fixture API contracts in Portfolio CI.

### Dry-Run Execution CI

Runs the dry-run adapter and dry-run API mount tests.

### Frontend Contract CI

Runs static Control Tower contract tests, including dry-run visibility and append-safety checks.

Replay UI behavior is additionally protected by fixture-backed UI snapshot contracts in Portfolio CI.

## Replay contract chain

Replay contract documentation starts here:

```text
docs/replay-contract-index.md
```

Replay contract tests:

```text
tests/test_outcome_replay_query.py
tests/test_outcome_replay_api_query.py
tests/test_replay_evidence_fixtures.py
tests/test_replay_fixture_api_contracts.py
tests/test_replay_fixture_ui_snapshot_contracts.py
tests/test_control_tower_ui.py
```

Replay fixtures:

```text
tests/fixtures/replay/
```

Replay contract docs:

```text
docs/replay-query-api.md
docs/replay-timeline-ui.md
docs/replay-result-drilldown-ux.md
docs/replay-analytics-summary-panel.md
docs/replay-export-snapshot-panel.md
docs/replay-evidence-regression-fixtures.md
docs/replay-fixture-api-contract-tests.md
docs/replay-fixture-ui-snapshot-contracts.md
docs/replay-contract-index.md
```

## Why this split exists

The repo previously used a large hardcoded pytest list inside Portfolio CI. That worked, but failures were harder to read. The new lanes make failures easier to diagnose without removing the broad portfolio gate.

## Important boundary

These CI lanes are offline/safe tests. They do not require broker secrets, market sessions, or live execution connectivity.

Replay tests are read-only contract checks. They must not add broker calls, order-management UI, runtime mutation, or execution adapters.

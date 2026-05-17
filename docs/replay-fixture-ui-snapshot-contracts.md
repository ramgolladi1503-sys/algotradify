# Replay Fixture UI Snapshot Contracts

PR 48 maps the replay regression fixtures into Control Tower UI snapshot contract checks.

## Goal

Prevent the replay UI from drifting away from the fixture-backed replay evidence and API contracts.

This builds on:

- PR 46: Replay Evidence Regression Fixtures
- PR 47: Replay Fixture API Contract Tests

## Test file

```text
tests/test_replay_fixture_ui_snapshot_contracts.py
```

## Fixture source

```text
tests/fixtures/replay/
```

Fixtures used:

```text
empty_replay.json
single_candidate_lifecycle.json
multi_candidate_mixed_status.json
```

## UI contract areas covered

The test checks that fixture-derived UI snapshots preserve:

- candidate count
- event count
- status distribution
- strategy distribution
- time-window min/max
- best/worst quality score
- grouped timeline
- status chain
- export snapshot keys

## Control Tower surfaces covered

The test verifies source terms for:

- Replay Analytics Summary Panel
- Replay Result Drilldown
- Replay Export Snapshot Panel
- copyable read-only JSON snapshot
- query metadata
- analytics summary
- grouped timeline

## Safety boundary

This PR is UI contract test hardening only.

It does not add:

- backend route behavior
- broker API calls
- real order placement
- order-management UI
- approval controls
- JSONL append behavior
- runtime mutation
- live or paper execution adapters

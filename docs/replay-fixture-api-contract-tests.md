# Replay Fixture API Contract Tests

PR 47 uses the deterministic replay fixtures from PR 46 against the `/outcome-replay` API.

## Goal

Prove the API response contract stays stable for replay data that the Control Tower depends on.

This builds on:

- PR 41: Replay Query API
- PR 42: Replay Timeline UI
- PR 43: Replay Result Drilldown UX
- PR 44: Replay Analytics Summary Panel
- PR 45: Replay Export Snapshot Panel
- PR 46: Replay Evidence Regression Fixtures

## Test file

```text
tests/test_replay_fixture_api_contracts.py
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

## API behavior covered

The tests validate:

- `/outcome-replay` returns HTTP 200 for fixture-backed runtime evidence
- expected fixture query cases produce deterministic event counts
- candidate identity fallback stays stable
- query metadata exposes `source_count` and `result_count`
- query metadata remains read-only
- empty replay fixture returns `NO_OUTCOME_EVENTS`
- no-match filters return `NO_OUTCOME_EVENTS`
- single-candidate lifecycle counts are stable
- nested `evidence.strategy_family` filtering is stable

## Safety boundary

This is API contract test coverage only.

It does not add:

- backend route behavior
- broker API calls
- real order placement
- order-management UI
- approval controls
- JSONL append behavior
- runtime mutation
- live or paper execution adapters

# Replay Evidence Regression Fixtures

PR 46 adds deterministic replay evidence fixtures for regression coverage.

## Goal

Prevent replay filtering, metadata, and Control Tower-facing fields from drifting silently.

This builds on:

- PR 41: Replay Query API
- PR 42: Replay Timeline UI
- PR 43: Replay Result Drilldown UX
- PR 44: Replay Analytics Summary Panel
- PR 45: Replay Export Snapshot Panel

## Fixture location

```text
tests/fixtures/replay/
```

## Fixtures

```text
empty_replay.json
single_candidate_lifecycle.json
multi_candidate_mixed_status.json
```

## Covered scenarios

The fixtures cover:

- empty replay results
- one candidate with full lifecycle progression
- multiple candidates with mixed statuses
- nested strategy evidence
- selected strategy-family fallback
- trade ID fallback for candidate identity
- no-match empty query results
- status aliases such as `ORDER_SUBMITTED`, `ORDER_ACCEPTED`, `ORDER_REJECTED`, `NO_ELIGIBLE_CANDIDATES`, and `POSITION_CLOSED`

## Stable fields

Fixtures intentionally preserve the fields expected by replay API and Control Tower views:

- `candidate_id`
- `trade_id`
- `status`
- `event`
- `strategy`
- `evidence.strategy_family`
- `selected.strategy_family`
- `ts_epoch`
- `quality_score`
- `score`

## Tests

Relevant test file:

```text
tests/test_replay_evidence_fixtures.py
```

The tests verify:

- fixture files exist
- fixture shape is stable
- expected counts match records
- query cases are deterministic
- query metadata remains read-only
- UI-facing contract terms remain present

## Safety boundary

This PR is test and fixture hardening only.

It does not add:

- backend route behavior
- broker API calls
- real order placement
- order-management UI
- approval controls
- JSONL append behavior
- runtime mutation
- live or paper execution adapters

# Replay Contract Index

This document is the single map for the replay API, Control Tower replay UI, replay fixtures, and replay contract tests.

Canonical path:

```text
docs/replay-contract-index.md
```

## Purpose

The replay layer exists to inspect historical and simulated outcome evidence safely.

It is not an execution surface.

## Replay PR chain

| Product PR | GitHub PR | Area | Document |
|---|---:|---|---|
| PR 41 | #46 | Replay Query API | `docs/replay-query-api.md` |
| PR 42 | #47 | Replay Timeline UI | `docs/replay-timeline-ui.md` |
| PR 43 | #48 | Replay Result Drilldown UX | `docs/replay-result-drilldown-ux.md` |
| PR 44 | #49 | Replay Analytics Summary Panel | `docs/replay-analytics-summary-panel.md` |
| PR 45 | #50 | Replay Export Snapshot Panel | `docs/replay-export-snapshot-panel.md` |
| PR 46 | #51 | Replay Evidence Regression Fixtures | `docs/replay-evidence-regression-fixtures.md` |
| PR 47 | #52 | Replay Fixture API Contract Tests | `docs/replay-fixture-api-contract-tests.md` |
| PR 48 | #53 | Replay Fixture UI Snapshot Contracts | `docs/replay-fixture-ui-snapshot-contracts.md` |

## Source code map

| Area | Path |
|---|---|
| Replay query helpers | `outcome_replay/query.py` |
| Replay normalization | `outcome_replay/replay.py` |
| Replay API tests | `tests/test_outcome_replay_api_query.py` |
| Replay query tests | `tests/test_outcome_replay_query.py` |
| Replay fixture tests | `tests/test_replay_evidence_fixtures.py` |
| Replay fixture API tests | `tests/test_replay_fixture_api_contracts.py` |
| Replay fixture UI tests | `tests/test_replay_fixture_ui_snapshot_contracts.py` |
| Control Tower UI contract tests | `tests/test_control_tower_ui.py` |
| Replay fixtures | `tests/fixtures/replay/` |
| Control Tower entry | `frontend/main.jsx` |
| Control Tower cards | `frontend/controlTowerCards.jsx` |

## Runtime artifact contract

The replay API reads outcome replay evidence from runtime artifacts.

Primary artifact expected by tests:

```text
.runtime/outcome_replay_latest.json
```

Expected shape:

```json
{
  "outcome_replay": []
}
```

Each replay row may include:

- `candidate_id`
- `trade_id`
- `client_order_id`
- `status`
- `outcome_status`
- `event`
- `current_status`
- `strategy`
- `strategy_id`
- `strategy_family`
- `setup_family`
- `evidence.strategy_family`
- `selected.strategy_family`
- `ts_epoch`
- `timestamp`
- `time`
- `created_at`
- `quality_score`
- `trade_quality_score`
- `score`

## Query contract

The replay API supports read-only filters:

- `candidate_id`
- `status`
- `strategy`
- `ts_from_epoch`
- `ts_to_epoch`

The Control Tower builds the query string with `URLSearchParams` and omits empty fields.

## Query metadata contract

Responses include query metadata:

```json
{
  "source_count": 0,
  "result_count": 0,
  "read_only": true,
  "is_order_action": false
}
```

These fields are Control Tower safety signals. They must not be removed casually.

## Control Tower replay surfaces

Replay UI is split across these surfaces:

1. Replay Timeline UI
2. Replay Result Drilldown
3. Replay Analytics Summary Panel
4. Replay Export Snapshot Panel
5. Replay Contract Health Badge

### Replay Timeline UI

Purpose:

- show replay filters
- apply query-only reads
- show query metadata
- show backend replay counts

### Replay Result Drilldown

Purpose:

- group replay rows by candidate identity
- show ordered timeline events
- show status transition chain
- expose raw event evidence for inspection

### Replay Analytics Summary Panel

Purpose:

- show candidate count
- show event count
- show status distribution
- show strategy distribution
- show time-window min/max
- show best/worst quality score

### Replay Export Snapshot Panel

Purpose:

- render a copyable read-only JSON snapshot
- include filters
- include query metadata
- include analytics summary
- include grouped timeline
- include filtered events

It is a textarea-based frontend snapshot. It is not a backend file export.

### Replay Contract Health Badge

Purpose:

- surface this index path
- surface replay contract docs
- surface replay contract tests
- surface replay fixtures
- stay static and read-only

Portfolio CI proves the listed files exist. The badge does not perform runtime filesystem checks.

## Fixture contract

Fixture directory:

```text
tests/fixtures/replay/
```

Current fixtures:

- `empty_replay.json`
- `single_candidate_lifecycle.json`
- `multi_candidate_mixed_status.json`

Covered cases:

- empty replay result
- single candidate lifecycle
- multi-candidate mixed status
- status aliases
- nested strategy evidence
- selected strategy-family fallback
- trade ID fallback
- no-match query result

## Test contract chain

| Layer | Test file | Purpose |
|---|---|---|
| Replay query | `tests/test_outcome_replay_query.py` | Unit-level filtering and metadata behavior |
| Replay API query | `tests/test_outcome_replay_api_query.py` | API-level query behavior |
| Fixture stability | `tests/test_replay_evidence_fixtures.py` | Fixture shape and deterministic query cases |
| Fixture API | `tests/test_replay_fixture_api_contracts.py` | Fixture-backed API response stability |
| Fixture UI | `tests/test_replay_fixture_ui_snapshot_contracts.py` | Fixture-backed Control Tower replay terms |
| Contract badge | `tests/test_replay_contract_health_badge.py` | Static badge and replay index visibility |
| Control Tower UI | `tests/test_control_tower_ui.py` | Static UI safety and section coverage |

## Safety boundary

Replay is read-only.

Replay must not add:

- broker API calls
- real order placement
- order-management UI
- approval controls
- JSONL append behavior from the frontend
- runtime mutation
- live execution adapters
- paper execution adapters

Expected safe flags:

```json
{
  "read_only": true,
  "is_order_action": false
}
```

## Change rules

Before changing replay behavior, update the contract chain in this order:

1. fixture expectations
2. query tests
3. API contract tests
4. UI snapshot contract tests
5. Control Tower static tests
6. documentation

Do not change the UI first and hope the contracts catch up later. That is how replay evidence rots.

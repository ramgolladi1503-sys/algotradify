# Replay Query API

PR 41 adds read-only query filters for outcome replay.

## Endpoint

```text
GET /outcome-replay
```

Supported filters:

- `candidate_id`
- `status`
- `strategy`
- `ts_from_epoch`
- `ts_to_epoch`

The endpoint remains backward-compatible with the existing `candidate_id` filter.

## Examples

```text
/outcome-replay?candidate_id=c1
/outcome-replay?status=FILLED
/outcome-replay?status=FILLED,REJECTED
/outcome-replay?strategy=orb_retest
/outcome-replay?ts_from_epoch=100&ts_to_epoch=200
/outcome-replay?status=FILLED&strategy=orb_retest&ts_from_epoch=100&ts_to_epoch=200
```

## Query metadata

The response now includes a `query` block:

```json
{
  "candidate_id": "c1",
  "status": "FILLED",
  "strategy": "orb_retest",
  "ts_from_epoch": 100.0,
  "ts_to_epoch": 200.0,
  "source_count": 10,
  "result_count": 1,
  "read_only": true,
  "is_order_action": false
}
```

## Matching behavior

Status matching supports common aliases already used by replay normalization, including:

- `SELECTED`
- `BLOCKED`
- `SUBMITTED`
- `ACCEPTED`
- `REJECTED`
- `PARTIALLY_FILLED`
- `FILLED`
- `EXITED`
- `CLOSED`

Multiple statuses can be comma-separated.

Strategy matching checks:

- `strategy`
- `strategy_id`
- `strategy_family`
- `setup_family`
- nested `evidence.strategy_family`
- nested `selected.strategy_family`

Time-window filters are inclusive.

Events without timestamps are excluded when a time-window filter is provided.

## Safety boundary

Replay query is read-only.

It does not:

- call broker APIs
- create orders
- submit/modify/cancel/exit orders
- approve orders
- append JSONL artifacts
- mutate runtime state
- change live/paper execution behavior

The query metadata always returns:

```json
{
  "read_only": true,
  "is_order_action": false
}
```

## Tests

Relevant tests:

```text
tests/test_outcome_replay_query.py
tests/test_outcome_replay_api_query.py
```

They verify:

- candidate filter
- status filter
- comma-separated status filter
- strategy filter
- nested strategy filter
- inclusive time-window filter
- combined filters
- empty state when no events match
- read-only query metadata

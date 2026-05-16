# Replay Timeline UI

PR 42 surfaces the PR 41 replay query API in the Control Tower.

## Control Tower card

The replay card is titled:

```text
Replay Timeline UI
```

It is a read-only replay and search surface.

## Filters

The card sends query filters to:

```text
GET /outcome-replay
```

Supported UI filters:

- `candidate_id`
- `status`
- `strategy`
- `ts_from_epoch`
- `ts_to_epoch`

The frontend builds the query string with `URLSearchParams` and omits empty fields.

Example frontend calls:

```text
/outcome-replay
/outcome-replay?candidate_id=c1
/outcome-replay?status=FILLED
/outcome-replay?status=FILLED%2CREJECTED
/outcome-replay?strategy=orb_retest
/outcome-replay?ts_from_epoch=100&ts_to_epoch=200
/outcome-replay?status=FILLED&strategy=orb_retest&ts_from_epoch=100&ts_to_epoch=200
```

## Query metadata shown

The card displays backend query metadata:

- `source_count`
- `result_count`
- `read_only`
- `is_order_action`

Expected safe metadata:

```json
{
  "read_only": true,
  "is_order_action": false
}
```

If these flags are not safe, the card shows a metadata warning.

## Persistence

Replay query fields are stored in the existing Control Tower preferences object under `replayQuery`.

A compatibility shim preserves the older `replayCandidateId` preference shape by mapping it into `replayQuery.candidateId`.

## Safety boundary

This UI is read-only.

It does not add broker connectivity, order placement, order-management buttons, JSONL append behavior, runtime mutation, or live/paper execution adapters.

The frontend calls `/outcome-replay` only as a read endpoint.

## Tests

Relevant tests:

```text
tests/test_control_tower_ui.py
```

They verify:

- all replay query filters are visible
- backend query parameter names are used
- query metadata is visible
- safe flags are displayed
- old `replayCandidateId` wiring is removed
- no order-management labels are introduced
- `append=true` is not present in the frontend

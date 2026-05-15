# Dry-Run API Mount

PR 25 mounts the PR 24 dry-run evidence route through a dedicated FastAPI entrypoint:

```text
api.server_with_dry_run:app
```

This entrypoint imports the existing `api.server.app`, installs the dry-run route, and preserves the existing server behavior.

## Endpoint

```text
GET /dry-run-execution
```

Query params:

- `limit`, default `25`
- `min_quality_score`, default `50`
- `now_epoch`, optional
- `append`, default `false`

The endpoint consumes the existing server helpers for:

- top executable selection
- execution readiness records
- execution safety decision
- approval audit evidence
- matching readiness lookup
- runtime artifact root

## Preview behavior

`append=false` is the default. In that mode, the endpoint returns the dry-run result and writes no files.

## Append behavior

`append=true` writes append-only JSONL evidence under the runtime logs directory:

- `dry_run_order_intents.jsonl`
- `dry_run_lifecycle.jsonl`
- `outcome_replay.jsonl`

## Safety flags

All responses preserve:

```json
{
  "dry_run_only": true,
  "is_order_action": false,
  "broker_api_called": false
}
```

Created intent payloads also expose:

```json
{
  "real_order_id": null
}
```

## Why this entrypoint exists

Direct connector writes to the large `api/server.py` file were unreliable. This entrypoint makes the route runnable and testable without replacing the main server file.

A later cleanup PR can move the mount call directly into `api/server.py` when editing locally.

## Test command

```bash
pytest -q tests/test_dry_run_execution_adapter.py tests/test_dry_run_execution_api.py tests/test_dry_run_execution_api_mount.py
```

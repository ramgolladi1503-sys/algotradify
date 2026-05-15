# Dry-Run API Mount

PR 25 introduced a mounted FastAPI entrypoint:

```text
api.server_with_dry_run:app
```

PR 26 adds direct package-level mounting so importing the normal server module also exposes the route:

```text
api.server:app
```

The route installer is idempotent, so the transitional `api.server_with_dry_run:app` entrypoint remains safe and does not double-register the endpoint.

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

The frontend must not call `append=true`; append is reserved for explicit backend/operator workflows.

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

## Mount implementation

Direct replacement of the large `api/server.py` file was unreliable through the connector. PR 26 therefore mounts the dry-run route from `api/__init__.py` when the `api` package is imported. Tests prove the route is available from `api.server.app`.

A later local-edit cleanup can move the mount call directly into `api/server.py` if desired.

## Control Tower status

Control Tower visibility is still a follow-up. The frontend file is a large single-file React app, and replacing it through the connector is high-risk. The UI follow-up should add a read-only “Dry-Run Execution Adapter” card that calls `/dry-run-execution?limit=20` with default `append=false` only.

## Test command

```bash
pytest -q tests/test_dry_run_execution_adapter.py tests/test_dry_run_execution_api.py tests/test_dry_run_execution_api_mount.py tests/test_dry_run_execution_api_direct_mount.py
```

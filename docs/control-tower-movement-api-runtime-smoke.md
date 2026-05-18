# Control Tower Movement API Runtime Smoke Tests

PR 72 adds runtime smoke coverage for the Movement Opportunity API route used by the Control Tower panel.

## Why this exists

PR 70 added the Movement Opportunity Dashboard Read-only Panel.
PR 71 mounted the Movement Opportunity API on the main FastAPI app.

PR 72 proves the frontend-called route works through the main server path and stays safe.

## Runtime route smoke coverage

The tests call the main app directly:

```python
from api.server import app
```

and validate:

```text
GET /movement-opportunity
GET /movement-opportunity/schema
```

## Dashboard default query

The smoke test uses the default dashboard query from the movement panel:

```text
symbol=NIFTY
ts_epoch=77777
```

The test proves the route returns `200` and keeps:

```text
read_only=true
is_order_action=false
```

## Schema smoke coverage

The schema smoke test validates:

```text
route
method
read_only
is_order_action
openapi_contract.path
openapi_contract.schema_path
required_query_params
```

## OpenAPI smoke coverage

The OpenAPI smoke test proves the main app exposes:

```text
/movement-opportunity
/movement-opportunity/schema
```

with GET-only methods and required params:

```text
symbol
ts_epoch
```

## Idempotency smoke coverage

The direct route registration test proves movement routes are registered once on the main app.

## CI coverage

The smoke tests were added to:

```text
tests/test_movement_opportunity_api.py
```

That file already runs in API Contract CI, so this PR does not create fake unwired coverage.

## Scope boundary

This PR does not add UI, providers, ranking logic, broker logic, or runtime behavior. It only proves the mounted read-only route works from the main API path used by Control Tower.

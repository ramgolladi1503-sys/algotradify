# Movement Opportunity Main Server Mount

PR 71 makes the Movement Opportunity API available from the main FastAPI app used by the Control Tower.

## Why this PR exists

PR 68 added the read-only API route installer.
PR 69 locked the API schema contract.
PR 70 added a read-only Control Tower panel that calls:

```text
GET /movement-opportunity?symbol=<symbol>&ts_epoch=<timestamp>
```

The dashboard is only demo-safe if the API process backing the frontend exposes that route.

## Mount path

The main server already installs dry-run/evidence routes through:

```python
install_dry_run_execution_route(app, ...)
```

PR 71 mounts the movement opportunity route from inside that installer:

```python
install_movement_opportunity_route(app)
```

This avoids duplicating route setup and keeps registration idempotent.

## Exposed read-only routes

```text
GET /movement-opportunity
GET /movement-opportunity/schema
```

## Contract tests

`tests/test_dry_run_execution_api_direct_mount.py` now proves that importing:

```python
from api.server import app
```

exposes:

```text
/movement-opportunity
/movement-opportunity/schema
```

The tests also prove each route is registered once.

## Safety boundary

This PR does not add movement providers, dashboard controls, or runtime decision changes. It only makes the already read-only route available on the main app used by the frontend.

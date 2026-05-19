# Runtime Migration Lock

## Purpose

Runtime Correction PR 10 closes the runtime correction wave with a deterministic migration lock.

The lock does not add runtime behavior. It verifies that the corrected runtime posture remains intact after PRs 1–9.

## Command

```bash
python scripts/runtime_migration_lock.py
python scripts/runtime_migration_lock.py --json
```

## Contract

```text
runtime_migration_lock_v1
```

The checker is read-only and must always report:

```text
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
live_mode_touched=false
```

## What the lock verifies

### Native runtime ownership

- root `main.py` exists
- native source markers exist
- dynamic external-loader markers are absent
- safety-critical startup imports/calls remain present
- `runtime_contract.py` still detects native runtime source

### Guarded operator startup

- root `run_live.sh` exists
- LIVE startup requires explicit confirmation
- `DRY_RUN=true` blocks LIVE startup
- `ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true` is used for live startup
- `scripts/operator_boot.py` exposes preflight/SIM/PAPER/API-only commands
- `scripts/operator_boot.py` does not expose LIVE startup

### External fallback deprecation

- external fallback opt-in env exists only as temporary compatibility
- default external fallback remains disabled
- preflight contains external fallback deprecation check

### Read-only visibility endpoints

- `/runtime/ownership` is GET-only
- `/broker/auth/visibility` is GET-only
- no POST/PUT/PATCH/DELETE mutation route appears in those route files
- safe flags remain present in ownership/auth visibility payloads

### Actionless Control Tower helpers

- runtime ownership panel is read-only
- auth visibility panel is read-only
- both expose `allowed_actions=[]`
- forbidden order/live/token actions remain documented in panel models

### Handoff evidence

- Grill/GSD/Hermes handoff files exist for Runtime Correction PR 1 through PR 10

### Secret/runtime artifact guard

The checker fails if obvious runtime/secret artifacts are committed at known forbidden paths:

```text
.env
.runtime/kite_access_token
runtime/kite_access_token
kite_access_token
```

## What this PR deliberately does not do

- no root `main.py` change
- no root `run_live.sh` behavior change
- no operator command behavior change
- no broker API call
- no auth mutation
- no order behavior
- no dashboard action controls
- no paper/agent internals
- no live default change

## Test proof

```bash
python -m pytest tests/test_runtime_migration_lock.py -q
python scripts/runtime_migration_lock.py
```

The tests prove the checker passes the current repo and fails when critical regressions are injected into a temporary copied repo.

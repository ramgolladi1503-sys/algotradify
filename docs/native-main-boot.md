# Native Main Boot

## Purpose

Runtime Correction PR 5 promotes root `main.py` from wrapper/launcher mode to the native Algotradify trading runtime entrypoint.

This means `python main.py` now starts the imported runtime directly instead of dynamically loading another repository's `main.py`.

## What changed

Root `main.py` now contains the native startup flow that was imported from Tradebot runtime source.

The promoted entrypoint preserves safety-critical startup behavior:

- runtime guard import side effects
- config loading
- runtime mode/config alignment check
- runtime directory initialization
- event log validation/repair
- Kite startup credential validation
- LIVE/PAPER instance locking
- database readiness guard
- startup security enforcement
- trade log initialization
- stale risk halt auto-clear
- readiness gate handling
- orchestrator startup
- order reconciliation daemon lifecycle
- broker truth reconciler lifecycle

## What was removed

The root entrypoint no longer uses dynamic external runtime loading:

```text
importlib.util.spec_from_file_location
_load_runtime_main
runtime_root = resolve_runtime_root()
Algotradify runtime bootstrap failed
```

## What remains deferred

This PR does not promote root `run_live.sh`.

Root operator scripts, login-only, validate-only, and safe SIM/PAPER/UI boot commands belong to Runtime Correction PR 6.

## Runtime contract after PR 5

After promotion, default runtime resolution can prefer the repo root when native source markers exist.

Expected preflight posture:

```text
runtime_ownership=NATIVE
native_source_present=true
native_main_promoted=true
external_runtime_used=false
```

## Safety boundary

This PR must not:

- promote root `run_live.sh`
- add broker order behavior
- add auth endpoints
- add UI controls
- make LIVE the default
- change API/frontend/paper/agent behavior
- weaken startup safety checks

## Acceptance proof

```bash
python -m pytest tests/test_native_main_boot_contract.py -q
python -m pytest tests/test_runtime_contract.py tests/test_native_runtime_contract.py -q
python -m pytest tests/test_native_runtime_source_import.py -q
python scripts/preflight_runtime.py --json --no-create-runtime-dirs
```

The root `main.py` must contain native startup imports and safety calls, and must not contain dynamic external-loader markers.

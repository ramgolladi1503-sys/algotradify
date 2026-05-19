# Runtime Correction PR 5 — GSD Execution Plan

## Goal

Promote root `main.py` to the native runtime entrypoint while preserving safety-critical startup behavior and avoiding run-script/API/UI/broker scope.

## Minimal files

```text
main.py
runtime_contract.py
tests/test_native_main_boot_contract.py
tests/test_runtime_contract.py
tests/test_native_runtime_contract.py
tests/test_native_runtime_source_import.py
docs/native-main-boot.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR5-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR5-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR5-hermes.md
PROJECT_STATE.md
```

## Implementation approach

1. Replace wrapper root `main.py` with native runtime boot flow from imported Tradebot snapshot.
2. Preserve runtime guard, config, auth validation, instance lock, DB guard, startup security, readiness gate, orchestrator, and reconciliation lifecycle.
3. Remove dynamic external `main.py` loader behavior.
4. Make native repo root the default runtime root after promotion.
5. Keep root `run_live.sh` deferred to PR 6.
6. Update tests that previously expected wrapper behavior.
7. Add regression tests proving native main markers and safety calls.

## Commands

```bash
python -m pytest tests/test_native_main_boot_contract.py -q
python -m pytest tests/test_runtime_contract.py tests/test_native_runtime_contract.py -q
python -m pytest tests/test_native_runtime_source_import.py -q
python scripts/preflight_runtime.py --json --no-create-runtime-dirs
```

## What not to touch

```text
run_live.sh
api/
frontend/
paper_trading/
agent_system/
execution_safety/
execution_readiness/
movement_engine/
top_selector/
```

## Acceptance proof

The PR is complete when:

- root `main.py` is native
- dynamic external loader markers are absent
- safety-critical startup calls are present
- runtime ownership reports `NATIVE`
- root `run_live.sh` is still absent
- mini-agent handoff artifacts exist

## GSD verdict

Ship only root native main promotion. Operator commands belong to PR 6.

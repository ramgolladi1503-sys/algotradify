# Runtime Correction PR 4 — GSD Execution Plan

## Goal

Harden native runtime contract and preflight visibility after native source import, without changing runtime boot behavior.

## Minimal files

```text
runtime_contract.py
tests/test_native_runtime_contract.py
docs/native-runtime-contract.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR4-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR4-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR4-hermes.md
PROJECT_STATE.md
```

## Implementation approach

1. Add native source marker detection.
2. Add runtime ownership classification.
3. Add strict native mode using `ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true`.
4. Add external fallback opt-out using `ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=false`.
5. Add preflight fields for ownership, native source presence, main promotion, external allowed/used.
6. Keep default runtime resolution wrapper-compatible until PR 5.
7. Add tests proving strict native behavior and default compatibility.

## Commands

```bash
python -m pytest tests/test_runtime_contract.py tests/test_native_runtime_contract.py -q
ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true python scripts/preflight_runtime.py --json --no-create-runtime-dirs
```

## What not to touch

```text
main.py
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

- strict native mode reports repo root as runtime root when native markers exist
- strict native mode blocks external runtime fallbacks
- missing native markers fail closed
- default wrapper behavior remains until PR 5
- preflight exposes runtime ownership metadata
- handoff artifacts exist

## GSD verdict

Ship only the native contract/preflight hardening. Root boot promotion belongs to Runtime Correction PR 5.

# Runtime Correction PR 9 — GSD Execution Plan

## Goal

Deprecate external runtime fallback and disable silent external fallback by default while keeping explicit temporary compatibility opt-in.

## Minimal files

```text
runtime_contract.py
api/runtime_ownership.py
tests/test_runtime_contract.py
tests/test_native_runtime_contract.py
tests/test_runtime_ownership_api.py
docs/external-runtime-deprecation.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR9-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR9-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR9-hermes.md
PROJECT_STATE.md
```

## Implementation approach

1. Change `external_runtime_allowed()` default to false.
2. Keep strict native mode blocking all external fallback.
3. Keep explicit compatibility only with `ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=true`.
4. Prefer native root when native markers exist.
5. Expose preflight deprecation metadata.
6. Surface deprecation fields in runtime ownership API.
7. Update tests for default native-only behavior and explicit opt-in compatibility.
8. Add docs and handoff artifacts.

## Commands

```bash
python -m pytest tests/test_runtime_contract.py tests/test_native_runtime_contract.py tests/test_runtime_ownership_api.py -q
```

## What not to touch

```text
main.py
run_live.sh
scripts/operator_boot.py
api auth mutation surfaces
broker adapters
execution order paths
paper_trading/
agent_system/
```

## Acceptance proof

The PR is complete when:

- external fallback is disabled by default
- configured external roots are ignored by default
- explicit external opt-in still works temporarily
- preflight exposes deprecation metadata
- ownership API exposes deprecation fields
- tests prove all above

## GSD verdict

Ship only compatibility cleanup/deprecation. Final lock belongs to PR 10.

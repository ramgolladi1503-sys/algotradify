# Runtime Correction PR 1 — GSD Execution Plan

## Goal

Add a read-only runtime ownership audit that makes the current wrapper/native state visible and test-proven.

## Minimal files

```text
scripts/audit_runtime_ownership.py
tests/test_runtime_ownership_audit.py
docs/runtime-ownership-audit.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR1-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR1-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR1-hermes.md
PROJECT_STATE.md
```

## Implementation approach

1. Inspect source files and path markers only.
2. Do not import runtime modules.
3. Do not create runtime directories.
4. Do not call broker APIs.
5. Classify ownership as one of:
   - `WRAPPER_OR_EXTERNAL_COMPATIBLE`
   - `NATIVE_WITH_EXTERNAL_COMPATIBILITY`
   - `NATIVE`
6. Emit safe flags.
7. Add fixture tests for wrapper, native, and native-with-external-compat states.

## Commands

```bash
python scripts/audit_runtime_ownership.py --json
python -m pytest tests/test_runtime_ownership_audit.py -q
```

## What not to touch

```text
main.py
runtime_contract.py
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

- audit script exists
- tests cover wrapper and native states
- audit output is read-only and non-executing
- documentation explains why feature work should pause
- handoff artifacts exist

## GSD verdict

Ship only the audit. Do not start migration work in this PR.

# Runtime Correction PR 10 — GSD Execution Plan

## Goal

Close the runtime correction wave with a deterministic migration lock checker and regression tests.

## Minimal files

```text
scripts/runtime_migration_lock.py
tests/test_runtime_migration_lock.py
docs/runtime-migration-lock.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR10-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR10-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR10-hermes.md
PROJECT_STATE.md
```

## Implementation approach

1. Add read-only migration lock checker.
2. Check native root ownership markers and absence of wrapper loader markers.
3. Check guarded live startup markers.
4. Check safe operator commands and absence of LIVE command in operator boot CLI.
5. Check external runtime fallback deprecation markers.
6. Check read-only GET visibility routes and safe flags.
7. Check actionless Control Tower panel helpers.
8. Check Runtime Correction PR 1–10 handoff artifacts exist.
9. Check obvious runtime/secret artifacts are absent.
10. Add tests that inject regressions into temporary copied repo and prove the checker fails.

## Commands

```bash
python -m pytest tests/test_runtime_migration_lock.py -q
python scripts/runtime_migration_lock.py
python scripts/runtime_migration_lock.py --json
```

## What not to touch

```text
main.py
run_live.sh
scripts/operator_boot.py
runtime_contract.py
api runtime/auth behavior
broker adapters
execution order paths
paper_trading/
agent_system/
frontend/dashboard action controls
```

## Acceptance proof

The PR is complete when:

- migration lock passes current repo
- injected regressions fail the checker
- checker safe flags are read-only
- docs explain the lock
- Grill/GSD/Hermes handoffs exist

## GSD verdict

Ship only the final migration lock. Resume product work only after this PR is merged.

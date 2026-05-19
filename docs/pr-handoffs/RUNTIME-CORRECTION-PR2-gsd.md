# Runtime Correction PR 2 — GSD Execution Plan

## Goal

Add a read-only planner that reports how Tradebot source would be imported natively into algotradify, including markers, exclusions, collisions, and unresolved decisions.

## Minimal files

```text
scripts/plan_tradebot_native_import.py
tests/test_tradebot_native_import_plan.py
runtime_source_manifest.schema.json
docs/tradebot-native-import-plan.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR2-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR2-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR2-hermes.md
PROJECT_STATE.md
```

## Implementation approach

1. Validate required source markers: `main.py`, `core/`, `config/`.
2. Plan root file candidates and runtime directory candidates.
3. Discover candidate scripts but defer their import decisions.
4. Exclude secrets, tokens, logs, runtime files, DB files, virtualenvs, and generated files.
5. Mark collisions as unresolved decisions.
6. Emit safe flags proving no import or runtime behavior change occurred.
7. Add tests proving missing source, missing markers, clean candidate reporting, collisions, CLI JSON, and no mutation.

## Commands

```bash
python scripts/plan_tradebot_native_import.py --source ../tradebot --target . --json
python -m pytest tests/test_tradebot_native_import_plan.py -q
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
core/
config/
strategies/
dashboard/
run_live.sh
```

## Acceptance proof

The PR is complete when:

- import planner exists
- planner is read-only
- tests prove missing source and missing markers block
- tests prove clean candidates are reported without copying
- tests prove collisions are unresolved decisions
- safe flags are present
- handoff artifacts exist

## GSD verdict

Ship only the import plan. Actual source import belongs to Runtime Correction PR 3.

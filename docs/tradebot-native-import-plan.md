# Tradebot Native Import Plan

## Purpose

This document supports Runtime Correction PR 2 — Tradebot Source Import Manifest and Collision Report.

The goal is to plan a native Tradebot source import into algotradify without copying files or changing runtime behavior yet.

## Why this PR exists

Runtime Correction PR 1 exposed the runtime ownership boundary. PR 2 prevents a reckless import by producing a deterministic plan before any Tradebot source is copied.

This matters because algotradify already owns important product layers that must not be overwritten:

```text
api/
frontend/
paper_trading/
agent_system/
execution_safety/
execution_readiness/
movement_engine/
top_selector/
```

Blindly copying Tradebot into algotradify could destroy or silently change those layers.

## What the planner checks

`scripts/plan_tradebot_native_import.py` checks:

- source path exists
- source has required Tradebot markers: `main.py`, `core/`, `config/`
- source git metadata, when available
- planned root file imports
- planned directory imports
- curated candidate scripts
- excluded patterns
- protected target prefixes
- collisions
- unresolved decisions
- safe flags proving no import happened

## Required source markers

```text
main.py
core/
config/
```

If any marker is missing, the source is not treated as a valid Tradebot runtime source.

## Planned import candidates

Root files:

```text
main.py
run_live.sh
run_all.sh
requirements.txt
```

Directories:

```text
core/
config/
strategies/
dashboard/
ml/
models/
rl/
fixtures/
```

Candidate scripts are discovered and marked for curated decision. They are not blindly imported.

## Excluded files and directories

The planner excludes secrets, runtime data, logs, local environments, databases, and generated artifacts:

```text
.git/
.env
.env.*
.runtime/
runtime/
logs/
*.token
*.secret
*.db
*.sqlite
*.sqlite3
*.parquet
*.pyc
.venv/
venv/
```

These must never be imported into the repo.

## Protected target prefixes

The planner treats these algotradify-owned areas as protected:

```text
api/
frontend/
paper_trading/
agent_system/
execution_safety/
execution_readiness/
movement_engine/
top_selector/
```

Any future import touching those areas must be explicitly rejected unless a later PR gives a very specific reason. PR 2 does not allow that.

## Collision rules

Collisions are not auto-resolved.

Important examples:

1. `main.py` collision is deferred to Runtime Correction PR 5 — Root Native main.py Promotion.
2. `scripts/*` collisions require curated decisions because algotradify already has scripts.
3. Protected target prefixes are blocked.
4. Existing docs/tests are not overwritten by the import planner.

## Commands

```bash
python scripts/plan_tradebot_native_import.py --source ../tradebot --target . --json
python -m pytest tests/test_tradebot_native_import_plan.py -q
```

## Safety boundary

PR 2 is planning-only:

```json
{
  "read_only": true,
  "planning_only": true,
  "source_imported": false,
  "runtime_behavior_changed": false,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null,
  "live_mode_touched": false
}
```

## What this PR does not do

This PR does not:

- copy Tradebot source
- replace `main.py`
- modify `runtime_contract.py`
- modify API or frontend code
- modify paper or agent code
- start the bot
- call broker APIs
- add auth behavior
- add UI controls

## Next PR

Runtime Correction PR 3 — Native Runtime Source Import.

PR 3 may import source only after PR 2 has made collisions and excluded patterns explicit.

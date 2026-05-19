# Runtime Correction PR 6 — GSD Execution Plan

## Goal

Add guarded native operator boot commands after root `main.py` promotion.

## Minimal files

```text
run_live.sh
scripts/operator_boot.py
tests/test_operator_boot_commands.py
docs/operator-boot-commands.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR6-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR6-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR6-hermes.md
PROJECT_STATE.md
```

## Implementation approach

1. Add root `run_live.sh` as explicit guarded LIVE operator entrypoint.
2. Require exactly one action: validate-only, login-only, or start.
3. Require `--i-understand-live-risk` for LIVE start.
4. Reject `DRY_RUN=true` for LIVE start.
5. Add `scripts/operator_boot.py` for safe preflight, SIM, PAPER, and API-only startup.
6. Add tests proving live is not default and safe commands do not force LIVE.
7. Add docs and handoff artifacts.

## Commands

```bash
python -m pytest tests/test_operator_boot_commands.py -q
bash run_live.sh --help
python scripts/operator_boot.py --help
python scripts/operator_boot.py preflight
```

## What not to touch

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

## Acceptance proof

The PR is complete when:

- `./run_live.sh` cannot start LIVE without explicit confirmation
- safe operator CLI supports preflight, SIM, PAPER, and API-only startup
- tests prove SIM/PAPER/UI commands do not force LIVE
- docs define operator commands
- handoff artifacts exist

## GSD verdict

Ship only guarded operator boot commands. API/Control Tower wiring belongs to PR 7.

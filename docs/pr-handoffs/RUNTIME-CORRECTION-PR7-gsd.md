# Runtime Correction PR 7 — GSD Execution Plan

## Goal

Wire runtime ownership visibility into API and Control Tower as read-only status.

## Minimal files

```text
api/runtime_ownership.py
api/runtime_ownership_route.py
api/schemas.py
api/dry_run_execution_route.py
dashboard/runtime_ownership_panel.py
tests/test_runtime_ownership_api.py
tests/test_runtime_ownership_panel.py
docs/runtime-ownership-api.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR7-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR7-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR7-hermes.md
PROJECT_STATE.md
```

## Implementation approach

1. Add a pure read-only payload builder from runtime preflight.
2. Add GET-only `/runtime/ownership` route installer.
3. Add schema for runtime ownership response.
4. Install the route through the existing API route installation path.
5. Add read-only Control Tower panel normalizer/renderer helper.
6. Add tests for safe flags, GET-only route, no action affordances, and panel read-only contract.

## Commands

```bash
python -m pytest tests/test_runtime_ownership_api.py tests/test_runtime_ownership_panel.py -q
```

## What not to touch

```text
main.py
run_live.sh
scripts/operator_boot.py
frontend action controls
paper_trading/
agent_system/
execution order paths
broker adapters
```

## Acceptance proof

The PR is complete when:

- runtime ownership route is GET-only
- payload is read-only and audit-only
- route does not expose order verbs
- panel exposes no allowed actions
- tests prove broker/order/live flags are safe
- handoff artifacts exist

## GSD verdict

Ship only read-only runtime ownership visibility. Auth UX belongs to PR 8.

# Runtime Correction PR 8 — GSD Execution Plan

## Goal

Add local-only broker auth visibility and startup guidance without creating an auth mutation or broker action surface.

## Minimal files

```text
api/auth_visibility.py
api/auth_visibility_route.py
api/schemas.py
api/dry_run_execution_route.py
dashboard/auth_visibility_panel.py
tests/test_auth_visibility_api.py
tests/test_auth_visibility_panel.py
docs/broker-auth-visibility.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR8-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR8-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR8-hermes.md
PROJECT_STATE.md
```

## Implementation approach

1. Add local-only sanitized auth visibility payload builder.
2. Report credential/token shape only: presence, length, tail4, usable shape.
3. Add GET-only `/broker/auth/visibility` route.
4. Install route through the existing API route installation path.
5. Add read-only Control Tower auth visibility panel helper.
6. Add tests proving no raw token/secret exposure, no broker/profile probe, no token mutation, and no allowed actions.
7. Add docs and handoff artifacts.

## Commands

```bash
python -m pytest tests/test_auth_visibility_api.py tests/test_auth_visibility_panel.py -q
```

## What not to touch

```text
main.py
run_live.sh
scripts/operator_boot.py
core/auth_health.py broker profile validation behavior
broker adapters
execution order paths
paper_trading/
agent_system/
```

## Acceptance proof

The PR is complete when:

- `/broker/auth/visibility` is GET-only
- payload never exposes raw token or API secret
- payload says `broker_api_called=false`
- payload says `profile_probe_called=false`
- payload says `token_mutated=false`
- panel exposes `allowed_actions=[]`
- tests prove the safety flags and route constraints

## GSD verdict

Ship only read-only broker auth visibility. Any real auth/login workflow belongs outside PR 8 unless explicitly scoped later.

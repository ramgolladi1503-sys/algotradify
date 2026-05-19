# Runtime Correction PR 7 — Hermes Review

## Final diff review target

Runtime Correction PR 7 must stay limited to read-only runtime ownership visibility.

## Expected changed files

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

## Review checklist

- [ ] `/runtime/ownership` is GET-only
- [ ] Payload has `read_only=true`
- [ ] Payload has `audit_only=true`
- [ ] Payload has `is_order_action=false`
- [ ] Payload has `broker_api_called=false`
- [ ] Payload has `real_order_id=null`
- [ ] Payload has `live_mode_touched=false`
- [ ] Panel helper exposes `allowed_actions=[]`
- [ ] Panel helper lists forbidden actions
- [ ] No broker/auth/order/live/UI control behavior is added
- [ ] No runtime state mutation is added

## Final reviewer warning

Do not approve if this PR creates runtime controls. It is status visibility only.

## Hermes verdict

Accept only if API and dashboard additions are read-only, actionless, and test-covered.

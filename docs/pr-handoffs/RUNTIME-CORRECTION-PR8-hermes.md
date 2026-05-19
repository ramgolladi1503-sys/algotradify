# Runtime Correction PR 8 — Hermes Review

## Final diff review target

Runtime Correction PR 8 must stay limited to local-only broker auth visibility and startup guidance.

## Expected changed files

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

## Review checklist

- [ ] `/broker/auth/visibility` is GET-only
- [ ] Payload uses local files/env only
- [ ] No broker/profile probe is called
- [ ] No raw token is exposed
- [ ] No API secret is exposed
- [ ] No token mutation exists
- [ ] No login/logout/refresh endpoint exists
- [ ] No dashboard action controls exist
- [ ] No broker order behavior is added
- [ ] No live toggle/default change is added
- [ ] Tests cover safe flags and forbidden action categories

## Final reviewer warning

Do not approve if this PR becomes an auth workflow PR. It is visibility and operator guidance only.

## Hermes verdict

Accept only if auth visibility remains local-only, sanitized, read-only, and actionless.

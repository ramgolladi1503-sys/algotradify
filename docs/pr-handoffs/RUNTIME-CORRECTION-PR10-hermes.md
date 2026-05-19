# Runtime Correction PR 10 — Hermes Review

## Final diff review target

Runtime Correction PR 10 must stay limited to final migration lock checker, tests, docs, and handoff evidence.

## Expected changed files

```text
scripts/runtime_migration_lock.py
tests/test_runtime_migration_lock.py
docs/runtime-migration-lock.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR10-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR10-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR10-hermes.md
PROJECT_STATE.md
```

## Review checklist

- [ ] Checker is read-only
- [ ] Checker reports `is_order_action=false`
- [ ] Checker reports `broker_api_called=false`
- [ ] Checker reports `real_order_id=null`
- [ ] Checker reports `live_mode_touched=false`
- [ ] Checker verifies native main and absence of wrapper loader markers
- [ ] Checker verifies guarded `run_live.sh`
- [ ] Checker verifies operator boot has no LIVE command
- [ ] Checker verifies external fallback deprecation markers
- [ ] Checker verifies visibility routes are GET-only
- [ ] Checker verifies panels are actionless
- [ ] Checker verifies handoff evidence exists
- [ ] Tests inject regressions and prove checker fails
- [ ] No runtime/auth/order/UI behavior changed

## Final reviewer warning

Do not approve if this PR modifies runtime behavior. PR 10 is the lock, not another migration step.

## Hermes verdict

Accept only if the final correction wave is locked by deterministic, failing regression tests without expanding behavior.

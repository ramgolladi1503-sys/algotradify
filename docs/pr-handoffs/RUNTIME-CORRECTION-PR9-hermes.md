# Runtime Correction PR 9 — Hermes Review

## Final diff review target

Runtime Correction PR 9 must stay limited to external runtime fallback deprecation and temporary explicit compatibility opt-in.

## Expected changed files

```text
runtime_contract.py
api/runtime_ownership.py
tests/test_runtime_contract.py
tests/test_native_runtime_contract.py
tests/test_runtime_ownership_api.py
docs/external-runtime-deprecation.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR9-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR9-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR9-hermes.md
PROJECT_STATE.md
```

## Review checklist

- [ ] External fallback disabled by default
- [ ] Native repo root remains default when native markers exist
- [ ] Configured external env roots ignored by default
- [ ] Strict native mode blocks external fallback
- [ ] Explicit `ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=true` remains as temporary compatibility
- [ ] Preflight exposes deprecation metadata
- [ ] Runtime ownership API exposes deprecation fields
- [ ] Root `main.py` unchanged
- [ ] Root `run_live.sh` unchanged
- [ ] Operator boot commands unchanged
- [ ] No broker/auth/order/live/UI behavior added

## Final reviewer warning

Do not approve if this PR changes startup commands or removes explicit opt-in compatibility before PR 10.

## Hermes verdict

Accept only if external fallback is deprecated, native default is enforced, and compatibility remains explicit-only.

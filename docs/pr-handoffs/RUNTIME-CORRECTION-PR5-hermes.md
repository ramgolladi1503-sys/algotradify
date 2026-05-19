# Runtime Correction PR 5 — Hermes Review

## Final diff review target

Runtime Correction PR 5 must stay limited to root native `main.py` promotion and directly required runtime contract/tests/docs updates.

## Expected changed files

```text
main.py
runtime_contract.py
tests/test_native_main_boot_contract.py
tests/test_runtime_contract.py
tests/test_native_runtime_contract.py
tests/test_native_runtime_source_import.py
docs/native-main-boot.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR5-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR5-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR5-hermes.md
PROJECT_STATE.md
```

## Review checklist

- [ ] Root `main.py` no longer dynamically loads another repo's `main.py`
- [ ] Safety-critical startup imports remain present
- [ ] Safety-critical startup calls remain present
- [ ] `runtime_contract.py` reports `NATIVE` after main promotion
- [ ] Default runtime root prefers repo root after promotion
- [ ] Root `run_live.sh` is not introduced
- [ ] No API/frontend/paper/agent mutation
- [ ] No broker order behavior added
- [ ] No auth endpoint added
- [ ] LIVE is not made default
- [ ] Tests cover native main and regression boundaries

## Final reviewer warning

Do not approve if this PR becomes the run script/auth/UI PR. PR 5 is root native main promotion only.

## Hermes verdict

Accept only if root native main is promoted without weakening startup safety or expanding scope.

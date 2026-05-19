# Runtime Correction PR 4 — Hermes Review

## Final diff review target

Runtime Correction PR 4 must stay limited to native runtime contract and preflight hardening.

## Expected changed files

```text
runtime_contract.py
tests/test_native_runtime_contract.py
docs/native-runtime-contract.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR4-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR4-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR4-hermes.md
PROJECT_STATE.md
```

## Review checklist

- [ ] No root `main.py` replacement
- [ ] No root `run_live.sh` promotion
- [ ] No API/frontend/paper/agent mutation
- [ ] No broker/auth/live behavior
- [ ] Strict native mode detects native source root
- [ ] Strict native mode blocks external env/sibling/home roots
- [ ] Missing native source fails closed
- [ ] Default runtime resolution remains wrapper-compatible until PR 5
- [ ] Preflight reports runtime ownership metadata
- [ ] Tests cover positive and negative native contract cases

## Final reviewer warning

Do not approve if this PR changes actual runtime boot to repo root. Root boot promotion belongs to PR 5 after the wrapper `main.py` is replaced.

## Hermes verdict

Accept only if the diff stays limited to runtime contract/preflight metadata, tests, docs, project-state metadata, and handoff artifacts.

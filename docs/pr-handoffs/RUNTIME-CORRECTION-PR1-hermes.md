# Runtime Correction PR 1 — Hermes Review

## Final diff review target

Runtime Correction PR 1 must remain audit-only.

## Expected changed files

```text
scripts/audit_runtime_ownership.py
tests/test_runtime_ownership_audit.py
docs/runtime-ownership-audit.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR1-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR1-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR1-hermes.md
PROJECT_STATE.md
```

## Review checklist

- [ ] No runtime behavior change
- [ ] No `main.py` change
- [ ] No `runtime_contract.py` change
- [ ] No source import
- [ ] No API/frontend/paper/agent mutation
- [ ] Audit script is read-only
- [ ] Audit script does not import runtime modules
- [ ] Tests prove wrapper detection
- [ ] Tests prove native detection
- [ ] Tests prove no runtime file mutation
- [ ] Output contains safe flags
- [ ] Documentation explains why this was needed

## Final reviewer warning

Do not approve if this PR tries to fix runtime ownership. Runtime Correction PR 1 only exposes the current state. The fix starts in Runtime Correction PR 2 and later.

## Hermes verdict

Accept only if the diff stays limited to audit, tests, docs, project-state metadata, and handoff artifacts.

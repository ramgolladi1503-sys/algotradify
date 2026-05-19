# Runtime Correction PR 2 — Hermes Review

## Final diff review target

Runtime Correction PR 2 must remain planning-only.

## Expected changed files

```text
scripts/plan_tradebot_native_import.py
tests/test_tradebot_native_import_plan.py
runtime_source_manifest.schema.json
docs/tradebot-native-import-plan.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR2-grill.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR2-gsd.md
docs/pr-handoffs/RUNTIME-CORRECTION-PR2-hermes.md
PROJECT_STATE.md
```

## Review checklist

- [ ] No Tradebot source copied
- [ ] No `main.py` change
- [ ] No `runtime_contract.py` change
- [ ] No runtime behavior change
- [ ] No API/frontend/paper/agent mutation
- [ ] Planner is read-only
- [ ] Planner reports required source markers
- [ ] Planner reports exclusions
- [ ] Planner reports collisions
- [ ] Planner reports unresolved decisions
- [ ] Safe flags include `source_imported=false`
- [ ] Tests prove no target mutation

## Final reviewer warning

Do not approve if this PR imports code. Runtime Correction PR 2 only decides what the import would look like and where the collision risks are.

## Hermes verdict

Accept only if the final diff stays limited to planning, tests, docs, schema, project-state metadata, and handoff artifacts.

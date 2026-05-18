# PR 98 — Hermes Post-Code Review

## Changed files match scope

Yes. Final changed files are limited to:

```text
PROJECT_STATE.md
docs/paper-replay-dataset-builder.md
docs/pr-handoffs/PR-98-grill.md
docs/pr-handoffs/PR-98-gsd.md
docs/pr-handoffs/PR-98-hermes.md
tests/snapshots/paper_replay_dataset_schema_v1.json
tests/test_paper_replay_dataset.py
```

## Forbidden files touched

No forbidden files were touched.

Forbidden areas stayed untouched:

```text
api/
frontend/
dashboard/
agent_system/
broker_contract/
execution_safety/
execution_readiness/
paper_broker/
strategies/
movement_engine/
top_selector/
main.py
runtime wiring
ML/ranker modules
broker adapters
```

## Safety boundary verification

Preserved:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

No runtime behavior, API, dashboard, broker/live execution, order placement, strategy work, agent-system work, label generation, reward generation, expectancy, profitability validation, or ML/ranker feature was added.

## Tests prove behavior

PR98 adds tests proving:

- `paper_replay_dataset_schema_contract()` matches the v1 snapshot exactly.
- Required row-key order cannot drift silently.
- Required result-key order cannot drift silently.
- Safe flags cannot drift silently.
- Scope boundary cannot drift silently.
- Missing `payload_hash` blocks validation.
- Unknown schema versions block validation.
- Invalid row types block validation.
- Nested analysis fields block validation.
- Non-null real order ids block validation.
- `broker_api_called=true` blocks validation.
- Order-control action names do not enter the schema contract.

## Test commands

Focused:

```bash
python -m pytest tests/test_paper_replay_dataset.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_export_bundle.py tests/test_paper_scenarios.py tests/test_paper_evidence_persistence.py -q
```

## Execution note

Local pytest execution was attempted from this environment, but the environment could not resolve `github.com` to clone the branch. GitHub CI is required as the executable proof for this PR.

## Remaining risk

The main remaining risk is snapshot maintenance discipline: future schema changes must intentionally update the v1 snapshot or introduce a new schema version with migration rules. A casual snapshot update without explanation should be rejected.

## Reject before merge if

- CI fails.
- Any forbidden file appears in the final diff.
- Snapshot equality is weakened or removed.
- Unsafe rows pass validation.
- Analysis/profitability fields are allowed.
- Runtime/API/UI/broker/live/strategy/agent work appears.

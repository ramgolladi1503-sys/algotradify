# PR 98 — Grill Scope Review

## PR goal

Harden the PR97 paper replay dataset contract with exact v1 schema snapshot coverage and negative validation tests so downstream replay and research tooling cannot silently consume drifted rows.

## Files allowed to change

```text
PROJECT_STATE.md
docs/paper-replay-dataset-builder.md
docs/pr-handoffs/PR-98-grill.md
docs/pr-handoffs/PR-98-gsd.md
docs/pr-handoffs/PR-98-hermes.md
tests/snapshots/paper_replay_dataset_schema_v1.json
tests/test_paper_replay_dataset.py
```

## Files forbidden to touch

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
new strategy providers
broker adapters
```

## Safety boundary

PR98 is schema hardening only. It must preserve:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

No runtime wiring, API, UI, broker/live execution, strategy work, agent-system expansion, label generation, reward generation, expectancy, profitability validation, or ML/ranker features.

## Failure cases

- Required replay row key disappears.
- Required replay result key disappears.
- Safe flag value changes silently.
- Scope boundary changes silently.
- Unknown schema version is accepted.
- Invalid row type is accepted.
- Missing required row key is accepted.
- Nested analysis/profitability field is accepted.
- Broker/live/order-control leakage enters the contract.

## Negative tests

- Exact schema snapshot comparison.
- Required row-key order locked.
- Required result-key order locked.
- Safe flags locked.
- Scope boundary locked.
- Missing `payload_hash` blocks validation.
- Unknown schema version blocks validation.
- Invalid row type blocks validation.
- Nested `future_return` blocks validation.
- Non-null real order id blocks validation.
- `broker_api_called=true` blocks validation.
- Order-control action strings are absent from the schema contract.

## Acceptance proof

Focused:

```bash
python -m pytest tests/test_paper_replay_dataset.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_export_bundle.py tests/test_paper_scenarios.py tests/test_paper_evidence_persistence.py -q
```

## Merge blockers

Reject before merge if any forbidden file is touched, if schema drift is not snapshot-locked, if unsafe rows pass validation, if analysis/profitability fields are allowed, or if runtime/API/UI/broker/live/strategy/agent work appears.

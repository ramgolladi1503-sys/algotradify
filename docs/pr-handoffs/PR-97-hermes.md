# PR 97 — Hermes Diff Review and State Handoff

## Role

Reviewer/state recorder only. Review final diff against Grill scope. Do not implement product code.

## Grill artifact reviewed

Path: docs/pr-handoffs/PR-97-grill.md

## GSD artifact reviewed

Path: docs/pr-handoffs/PR-97-gsd.md

## Final changed files

- paper_trading/replay_dataset.py
- tests/test_paper_replay_dataset.py
- docs/paper-replay-dataset-builder.md
- paper_trading/__init__.py
- PROJECT_STATE.md
- docs/pr-handoffs/PR-97-grill.md
- docs/pr-handoffs/PR-97-gsd.md
- docs/pr-handoffs/PR-97-hermes.md

## Changed files match approved scope

Yes.

## Forbidden files touched

No.

Forbidden layers not touched:

```text
api/
frontend/
dashboard/
broker_contract/
execution_safety/
execution_readiness/
strategies/
movement_engine/
top_selector/
paper_broker/
agent_system/
main.py
runtime wiring
live execution paths
real broker adapters
credential/config files
```

## Safety boundary preserved

Yes.

The implementation is local paper replay dataset shaping only. It does not add expectancy/profitability validation, reward/label generation, ML/ranker features, backtest execution, runtime wiring, API/UI, broker/live behavior, strategy work, or agent-system work.

## Behavior tests added

Yes.

Tests cover valid bundle-to-row conversion, JSONL write/load, deterministic row IDs, deterministic rows, source identifier preservation, and no bundle mutation.

## Negative tests added

Yes.

Tests cover missing bundle root, invalid bundle, missing evidence, corrupt evidence, unsafe evidence, unsafe rows, forbidden analysis fields, output path inside bundle, corrupt dataset rows, and forbidden order-control text.

## Focused test command

```bash
python -m pytest tests/test_paper_replay_dataset.py -q
```

## Adjacent regression command

```bash
python -m pytest tests/test_paper_export_bundle.py tests/test_paper_scenarios.py tests/test_paper_evidence_persistence.py -q
```

Additional paper truth regression:

```bash
python -m pytest tests/test_paper_session_boundary.py tests/test_paper_trading_pipeline.py tests/test_paper_state_reconciliation.py -q
```

## CI status

Pending.

## Remaining risks

- Replay rows are minimal and source-traceable only. They intentionally do not include labels, rewards, future returns, or profitability fields.
- Output files are blocked inside the bundle root to preserve export bundle immutability.
- Future PR98 should harden the replay row schema and snapshot contracts before downstream replay/research work expands.

## Reject before merge if

- Runtime wiring appears.
- API/UI/dashboard work appears.
- Broker/live execution appears.
- Strategy/ranker work appears.
- Agent-system files are touched.
- Expectancy/profitability/reward/label generation appears.
- Backtest execution appears.
- Bundle validation is bypassed.
- Unsafe evidence or unsafe rows are accepted successfully.
- Stage-gate workflow fails due to missing handoff evidence.

## State update after merge

Latest merged PR: GitHub PR TBD / Product PR 97 — Paper Replay Dataset Builder
Product PR: PR 97
Next PR only: PR 98 — Replay Dataset Schema Hardening and Snapshot Contracts
What not to touch next: broker/live/API/UI/dashboard/strategy/ML/agent-system unless explicitly scoped by roadmap.

## Hermes verdict

Approve, pending CI.

# PR 97 — GSD Implementation Handoff

## Role

Builder only. Implement approved Grill scope. Do not expand scope.

## Grill artifact used

Path: docs/pr-handoffs/PR-97-grill.md

## Approved files changed

- paper_trading/replay_dataset.py
- tests/test_paper_replay_dataset.py
- docs/paper-replay-dataset-builder.md
- paper_trading/__init__.py
- PROJECT_STATE.md
- docs/pr-handoffs/PR-97-gsd.md
- docs/pr-handoffs/PR-97-hermes.md

## Actual files changed

- paper_trading/replay_dataset.py
- tests/test_paper_replay_dataset.py
- docs/paper-replay-dataset-builder.md
- paper_trading/__init__.py
- PROJECT_STATE.md
- docs/pr-handoffs/PR-97-grill.md
- docs/pr-handoffs/PR-97-gsd.md
- docs/pr-handoffs/PR-97-hermes.md

## Implementation summary

Added a deterministic local paper replay dataset builder.

The builder:

1. Validates a PR96 export bundle before reading bundle evidence.
2. Loads the export manifest.
3. Reads exported evidence JSONL from the bundle layout.
4. Converts eligible evidence records into source-traceable replay rows.
5. Preserves bundle id, record id, cycle id, candidate id, strategy id, scenario name, pipeline status, event count, session id, and payload hash.
6. Preserves explicit paper-only safe flags.
7. Optionally writes replay rows to a local JSONL file outside the export bundle.
8. Loads and validates replay JSONL rows.
9. Blocks unsafe evidence, unsafe rows, corrupt JSONL, bundle validation failures, output-path bundle mutation, and forbidden analysis/profitability fields.

No expectancy/profitability validation, reward/label generation, ML/ranker features, backtest execution, runtime wiring, API, UI/dashboard, broker execution, LIVE execution, new strategies, or agent-system work was added.

## Tests added

- schema contract exposes safe flags and JSONL output
- valid export bundle builds replay rows
- valid replay rows can be written and loaded
- missing bundle root blocks
- invalid bundle blocks
- missing evidence file blocks
- corrupt evidence JSONL blocks
- unsafe evidence record blocks
- unsafe replay row blocks validation
- output has no order controls
- dataset does not include expectancy/profitability/reward/label fields
- analysis fields in evidence block dataset build
- same input produces deterministic rows
- builder does not mutate export bundle files
- output path inside bundle blocks
- load missing dataset returns EMPTY
- load corrupt dataset blocks
- stable replay row id is deterministic

## Negative tests added

The suite blocks missing inputs, invalid bundles, missing/corrupt evidence, unsafe evidence, unsafe rows, forbidden analysis fields, output paths inside the bundle, corrupt dataset rows, and forbidden order-control text.

## Commands run

Focused:

```bash
python -m pytest tests/test_paper_replay_dataset.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_export_bundle.py tests/test_paper_scenarios.py tests/test_paper_evidence_persistence.py -q
```

Additional paper truth regression:

```bash
python -m pytest tests/test_paper_session_boundary.py tests/test_paper_trading_pipeline.py tests/test_paper_state_reconciliation.py -q
```

Note: implementation was applied remotely through GitHub connector, so CI must confirm actual execution.

## Safety proof

Every replay dataset result and row exposes:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

The builder refuses to write output inside the export bundle so dataset creation does not mutate bundle artifacts.

## Scope deviations

None from approved Grill scope.

The optional CLI was intentionally not added.

## What was intentionally not touched

- no expectancy/profitability validation
- no reward/label generation
- no ML/ranker features
- no backtest execution
- no runtime wiring
- no API
- no UI/dashboard
- no broker/live execution
- no strategy/provider work
- no agent-system work
- no mutation to export bundle/persistence/scenario/session/pipeline contracts

## GSD verdict

Ready for Hermes review.

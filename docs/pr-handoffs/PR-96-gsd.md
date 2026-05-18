# PR 96 — GSD Implementation Handoff

## Role

Builder only. Implement approved Grill scope. Do not expand scope.

## Grill artifact used

Path: docs/pr-handoffs/PR-96-grill.md

## Approved files changed

- paper_trading/export_bundle.py
- tests/test_paper_export_bundle.py
- docs/paper-evidence-export-bundle.md
- paper_trading/__init__.py
- PROJECT_STATE.md
- docs/pr-handoffs/PR-96-gsd.md
- docs/pr-handoffs/PR-96-hermes.md

## Actual files changed

- paper_trading/export_bundle.py
- tests/test_paper_export_bundle.py
- docs/paper-evidence-export-bundle.md
- paper_trading/__init__.py
- PROJECT_STATE.md
- docs/pr-handoffs/PR-96-grill.md
- docs/pr-handoffs/PR-96-gsd.md
- docs/pr-handoffs/PR-96-hermes.md

## Implementation summary

Added a deterministic local paper evidence export bundle layer.

The layer:

1. Loads validated paper evidence records through PR93 persistence.
2. Accepts optional scenario result payloads.
3. Writes local bundle files.
4. Generates manifest.json.
5. Generates checksums.json.
6. Writes evidence/paper_evidence.jsonl.
7. Writes scenarios/scenario_results.json.
8. Validates required files and checksum integrity.
9. Blocks unsafe evidence, unsafe scenario results, replay dataset leakage, and expectancy/profitability leakage.

No replay dataset generation, expectancy/profitability validation, runtime wiring, API, UI/dashboard, broker execution, LIVE execution, strategy/provider work, ML/ranker work, cloud upload, or report/dashboard layer was added.

## Tests added

- schema contract exposes safe flags and bundle layout
- valid evidence export builds bundle
- validate built bundle returns VALID
- missing bundle_root blocks
- missing evidence_path blocks
- corrupt evidence load blocks
- unsafe evidence record blocks
- scenario result with unsafe flag blocks
- checksum mismatch blocks validation
- missing manifest blocks validation
- missing evidence file blocks validation
- bundle result has no order controls
- export bundle does not create replay dataset file
- export bundle does not compute expectancy or profitability fields
- same input produces deterministic manifest and checksums
- load paper export manifest returns manifest
- stable file hash changes when file changes

## Negative tests added

The suite blocks missing inputs, corrupt evidence, unsafe evidence, unsafe scenario results, checksum mismatches, missing manifest, missing evidence file, forbidden replay dataset output, forbidden expectancy/profitability fields, and forbidden order-control text.

## Commands run

Focused:

```bash
python -m pytest tests/test_paper_export_bundle.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_scenarios.py tests/test_paper_evidence_persistence.py tests/test_paper_session_boundary.py -q
```

Additional paper truth regression:

```bash
python -m pytest tests/test_paper_trading_pipeline.py tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py -q
```

Note: implementation was applied remotely through GitHub connector, so CI must confirm actual execution.

## Safety proof

Every bundle result and manifest exposes:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

Bundle output remains local filesystem only and does not create replay datasets or expectancy/profitability outputs.

## Scope deviations

None from approved Grill scope.

The optional CLI was intentionally not added.

## What was intentionally not touched

- no replay dataset generation
- no expectancy/profitability validation
- no runtime wiring
- no API
- no UI/dashboard
- no broker/live execution
- no strategy/provider work
- no ML/ranker work
- no cloud upload
- no mutation to persistence/scenario/session/pipeline contracts

## GSD verdict

Ready for Hermes review.

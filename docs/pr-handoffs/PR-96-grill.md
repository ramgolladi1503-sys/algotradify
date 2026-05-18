# PR 96 — Grill Scope Review

## Role

Grill reviewer only. No product implementation. No code files changed in this stage.

## Proposed PR

PR 96 — Paper Evidence Export Bundle

## Why this PR is next

PR 87 created the canonical paper event journal.
PR 88 created the deterministic paper state reducer.
PR 89 added event ordering and idempotency guard.
PR 90 added deterministic rebuild from journal.
PR 91 added reconciliation between rebuilt and observed state.
PR 92 added a minimal in-memory paper trading pipeline orchestrator.
PR 93 added local JSONL paper evidence persistence.
PR 94 added non-destructive paper session boundaries and reset markers.
PR 95 added deterministic end-to-end paper scenarios.

The next missing step is packaging paper evidence into a deterministic export bundle. PR95 proves controlled scenarios can run through session boundary, pipeline, persistence, and evidence reload. PR96 should make that evidence portable and reviewable for later replay/research work.

This PR must not generate replay datasets, compute expectancy, add dashboards, add APIs, wire runtime, or touch broker/live behavior.

## Scope decision

Approved with strict limits.

PR96 may add a local paper evidence export bundle builder and validator. It should package existing paper evidence files and scenario outputs into a deterministic bundle directory or archive-ready folder structure with manifest, hashes, schema versions, and safety metadata.

## Goal

Create a paper-only export bundle layer that can:

1. Read local paper evidence records.
2. Read or accept scenario result payloads.
3. Build a deterministic export manifest.
4. Copy/write bundle evidence files into a local export directory.
5. Include hashes/checksums for exported files and payloads.
6. Validate bundle structure and safe flags.
7. Fail closed on unsafe/corrupt evidence.

The bundle should support future replay/research work, but PR96 itself should not generate replay datasets or compute trading performance.

## Files allowed to change

Expected files:

```text
paper_trading/export_bundle.py
tests/test_paper_export_bundle.py
docs/paper-evidence-export-bundle.md
paper_trading/__init__.py
PROJECT_STATE.md
docs/pr-handoffs/PR-96-gsd.md
docs/pr-handoffs/PR-96-hermes.md
```

Optional only if strongly justified:

```text
scripts/export_paper_evidence_bundle.py
```

Recommendation: do not add CLI in PR96 unless it stays tiny and only wraps the core API. Core API + tests is enough.

## Files forbidden to touch

```text
api/
frontend/
broker_contract/
execution_safety/
execution_readiness/
strategies/
movement_engine/
top_selector/
paper_broker/
main.py
runtime wiring
live execution paths
real broker adapters
credential/config files
```

Also forbidden unless a blocking contract bug is proven and separately scoped:

```text
paper_trading/event_journal.py
paper_trading/events.py
paper_trading/state_reducer.py
paper_trading/event_ordering.py
paper_trading/rebuild.py
paper_trading/reconciliation.py
paper_trading/pipeline.py
paper_trading/persistence.py
paper_trading/session_boundary.py
paper_trading/scenarios.py
```

PR96 may import and use persistence/scenario outputs. It must not mutate their contracts.

## Safety boundary

All export results and manifests must expose:

```text
paper_only=true
read_only=true where applicable
is_order_action=false
broker_api_called=false
real_order_id=null
```

Export writing is local filesystem writing only. It must still expose:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

No real broker execution.
No LIVE orders.
No order submit/modify/cancel/exit controls.
No API endpoint.
No UI/dashboard.
No runtime wiring.
No strategy/provider work.
No ML/ranker work.
No credential usage.
No replay dataset generation.
No expectancy/profitability validation.

## Approved design shape

The builder may add:

```text
PaperExportBundleStatus
PaperExportBundleResult
paper_export_bundle_schema_contract()
build_paper_export_bundle()
validate_paper_export_bundle()
load_paper_export_manifest()
stable_file_hash()
```

Recommended statuses:

```text
BUILT
VALID
EMPTY
BLOCKED
```

Recommended bundle layout:

```text
bundle_root/
  manifest.json
  evidence/
    paper_evidence.jsonl
  scenarios/
    scenario_results.json
  checksums.json
```

Keep the layout simple. Do not add compression, cloud upload, UI links, or replay conversion.

## Recommended manifest fields

```text
schema_version
bundle_type
bundle_id
created_at_epoch
source_evidence_path
record_count
scenario_count
files
checksums
safe_flags
paper_only
read_only
is_order_action
broker_api_called
real_order_id
```

If scenario results are included, they should remain scenario evidence, not replay data.

## Required behavior

1. Require bundle_root.
2. Require evidence_path or explicit evidence records.
3. Load evidence through PR93 persistence loader.
4. Block if persistence load is BLOCKED.
5. Allow EMPTY evidence only if explicitly documented and tested.
6. Validate all loaded records preserve paper-only safe flags.
7. Write manifest.json deterministically.
8. Write/copy evidence JSONL into bundle/evidence.
9. Write scenario results if provided.
10. Write checksums.json.
11. Validate all expected bundle files exist.
12. Validate checksums match.
13. Never call broker or runtime code.
14. Never generate replay dataset rows.
15. Never compute expectancy/profitability.

## What PR96 must not do

Do not add replay dataset generation. That starts PR97.
Do not add outcome labels or reward calculation.
Do not add expectancy validation or profitability scoring.
Do not add runtime scheduler integration.
Do not add API/UI/dashboard.
Do not call brokers.
Do not touch live mode.
Do not implement strategy logic.
Do not add new movement providers.
Do not add ML/ranker work.
Do not upload bundles to cloud.
Do not create reports that pretend to prove profitability.

## Failure cases

The export bundle layer must fail closed on:

```text
missing bundle_root
missing evidence_path when required
persistence load BLOCKED
corrupt evidence file
non-object evidence record
unsafe evidence flags
broker_api_called=true anywhere
is_order_action=true anywhere
real_order_id present anywhere
invalid scenario result payload
unsafe scenario result flags
manifest write failure if surfaced
missing expected bundle file during validation
checksum mismatch
unknown bundle schema version
attempt to include replay dataset output
attempt to include expectancy/profitability output
```

## Negative tests required

Minimum required tests:

```text
schema contract exposes safe flags and bundle layout
valid evidence export builds bundle
manifest contains schema version, bundle id, files, checksums, safe flags
exported evidence file exists
checksums file exists
validate built bundle returns VALID
missing bundle_root blocks
missing evidence_path blocks
corrupt evidence load blocks
unsafe evidence record blocks
scenario result with unsafe flag blocks
checksum mismatch blocks validation
missing manifest blocks validation
missing evidence file blocks validation
bundle result has no submit/modify/cancel/exit/place controls
export bundle does not create replay dataset file
export bundle does not compute expectancy/profitability fields
same input produces deterministic manifest/checksums except allowed created_at if explicitly controlled
```

## Acceptance proof required

Focused:

```bash
python -m pytest tests/test_paper_export_bundle.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_scenarios.py tests/test_paper_evidence_persistence.py tests/test_paper_session_boundary.py -q
```

Additional paper truth regression if export imports broader contracts:

```bash
python -m pytest tests/test_paper_trading_pipeline.py tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py -q
```

## Regression risks

1. Export code can turn into a report/dashboard layer. Do not add presentation logic.
2. Export code can accidentally become replay generation. Keep replay out.
3. Manifest determinism can become fragile if timestamps are uncontrolled. Require explicit created_at_epoch or document controlled behavior.
4. Bundle validation must fail on missing/corrupt files, not silently pass.
5. Scenario evidence may need richer metadata later, but do not overbuild now.

## Merge blockers

Block merge if any of these happen:

```text
broker/live files touched
API or UI files touched
runtime scheduler/main wiring touched
new strategy/provider/ranker logic added
replay dataset generated
expectancy/profitability scoring added
cloud upload added
scenario/persistence contracts changed without separate scope
unsafe evidence included successfully
checksum mismatch is ignored
missing bundle files are ignored
PR lacks GSD and Hermes artifacts
```

## Required GSD instruction

Builder must not code until this Grill artifact is accepted.

Builder must create:

```text
docs/pr-handoffs/PR-96-gsd.md
```

The GSD artifact must list implementation choices, actual files changed, tests added, commands, and any deviation from this Grill scope.

## Required Hermes instruction

Reviewer must create after implementation:

```text
docs/pr-handoffs/PR-96-hermes.md
```

Hermes must compare the actual changed files against this Grill scope and explicitly approve, request changes, or reject.

## Final Grill verdict

Approved for a deterministic local Paper Evidence Export Bundle only.

Do not implement replay dataset generation, expectancy/profitability validation, runtime wiring, API, UI/dashboard, broker execution, live execution, new strategies, or ML/ranker work in PR96.

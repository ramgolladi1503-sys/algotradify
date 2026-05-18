# PR 97 — Grill Scope Review

## Role

Grill reviewer only. No product implementation. No code files changed in this stage.

## Proposed PR

PR 97 — Paper Replay Dataset Builder

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
PR 96 added deterministic local paper evidence export bundles.

The next missing step is turning exported paper evidence into replay-ready research rows. PR96 packages evidence, but it does not create a dataset. PR97 should build a deterministic replay dataset from a validated export bundle without scoring profitability, training models, wiring runtime, or exposing APIs/UI.

This PR is a data-shaping step only. It must not become expectancy/profitability validation, ML/ranker work, strategy work, dashboard work, broker/live work, or runtime replay execution.

## Scope decision

Approved with strict limits.

PR97 may add a local paper replay dataset builder and validator that reads a PR96 export bundle, validates manifest/checksums, parses paper evidence records, and emits deterministic replay dataset rows.

## Goal

Create a paper-only replay dataset layer that can:

1. Load and validate a PR96 export bundle.
2. Read exported paper evidence records.
3. Convert eligible evidence into deterministic replay rows.
4. Preserve safe flags.
5. Include source references back to bundle/evidence records.
6. Write a local replay dataset JSONL or return rows in memory.
7. Validate replay dataset schema and safety.
8. Fail closed on unsafe/corrupt/missing evidence.

The dataset should support later replay/research work, but PR97 itself must not compute outcomes, expectancy, profitability, rewards, labels, or ML features beyond basic replay-safe fields.

## Files allowed to change

Expected files:

```text
paper_trading/replay_dataset.py
tests/test_paper_replay_dataset.py
docs/paper-replay-dataset-builder.md
paper_trading/__init__.py
PROJECT_STATE.md
docs/pr-handoffs/PR-97-gsd.md
docs/pr-handoffs/PR-97-hermes.md
```

Optional only if strongly justified:

```text
scripts/build_paper_replay_dataset.py
```

Recommendation: do not add CLI in PR97 unless it stays tiny and only wraps the core API. Core API + tests is enough.

## Files forbidden to touch

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
paper_trading/export_bundle.py
```

PR97 may import and use export bundle helpers. It must not mutate their contracts.

## Safety boundary

All replay dataset results and rows must expose:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

Dataset writing is local filesystem writing only. It must still expose:

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
No expectancy/profitability validation.
No reward calculation.
No label generation.
No feature engineering beyond minimal replay-safe metadata.

## Approved design shape

The builder may add:

```text
PaperReplayDatasetStatus
PaperReplayDatasetResult
paper_replay_dataset_schema_contract()
build_paper_replay_dataset()
validate_paper_replay_dataset_rows()
load_paper_replay_dataset_rows()
stable_replay_row_id()
```

Recommended statuses:

```text
BUILT
VALID
EMPTY
BLOCKED
```

Recommended output format:

```text
JSONL
```

Recommended row fields:

```text
schema_version
row_type
row_id
source_bundle_id
source_record_id
source_record_type
source_cycle_id
source_candidate_id
source_strategy_id
source_created_at_epoch
scenario_name
event_count
pipeline_status
session_id
payload_hash
paper_only
read_only
is_order_action
broker_api_called
real_order_id
```

Keep rows minimal. Do not add PnL labels, future return labels, expected value, reward, win/loss, model features, or trading decisions in PR97.

## Required behavior

1. Require bundle_root.
2. Validate bundle through PR96 export bundle validator.
3. Load manifest through PR96 export bundle loader.
4. Read exported evidence JSONL from the bundle layout.
5. Parse evidence records deterministically.
6. Select eligible paper evidence records only.
7. Convert eligible records into replay rows.
8. Preserve safe flags.
9. Include source identifiers and hashes.
10. Optionally write replay_dataset.jsonl locally if output_path is provided.
11. Validate rows after build.
12. Fail closed on corrupt evidence, unsafe records, unsafe rows, missing bundle files, checksum mismatch, unknown schema version, or forbidden outcome/profitability fields.

## What PR97 must not do

Do not compute realized outcome labels.
Do not compute expectancy.
Do not compute profitability.
Do not compute rewards.
Do not create ML/ranker features.
Do not add model training.
Do not add backtest engine.
Do not add runtime replay executor.
Do not add API/UI/dashboard.
Do not call brokers.
Do not touch live mode.
Do not implement strategy logic.
Do not add new movement providers.
Do not mutate export bundle behavior.

## Failure cases

The replay dataset layer must fail closed on:

```text
missing bundle_root
missing manifest
invalid manifest
bundle validation BLOCKED
missing evidence file
corrupt evidence JSONL
non-object evidence record
unsafe evidence flags
broker_api_called=true anywhere
is_order_action=true anywhere
real_order_id present anywhere
unknown evidence schema version if required
missing source identifiers
replay row missing required key
replay row unsafe flags
output path parent invalid if writing
attempt to include expectancy/profitability/reward/label fields
attempt to include broker/live/order-action controls
```

## Negative tests required

Minimum required tests:

```text
schema contract exposes safe flags and JSONL output
valid export bundle builds replay rows
valid replay rows can be written and loaded
row contains source bundle id and source record id
row preserves paper_only/read_only/is_order_action/broker_api_called/real_order_id flags
missing bundle_root blocks
invalid bundle blocks
missing evidence file blocks
corrupt evidence JSONL blocks
unsafe evidence record blocks
unsafe replay row blocks validation
output has no submit/modify/cancel/exit/place controls
dataset does not include expectancy/profitability/reward/label fields
same input produces deterministic rows
builder does not mutate export bundle files
```

## Acceptance proof required

Focused:

```bash
python -m pytest tests/test_paper_replay_dataset.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_export_bundle.py tests/test_paper_scenarios.py tests/test_paper_evidence_persistence.py -q
```

Additional paper truth regression if replay imports broader contracts:

```bash
python -m pytest tests/test_paper_session_boundary.py tests/test_paper_trading_pipeline.py tests/test_paper_state_reconciliation.py -q
```

## Regression risks

1. Replay dataset can accidentally become profitability labeling. Do not add labels/rewards/expectancy.
2. Dataset row schema can become too wide too early. Keep minimal source-traceable fields.
3. Bundle validation must be reused, not bypassed.
4. Writing dataset files must not mutate bundle files.
5. Agent runtime PRs recently merged; PR97 must not touch `agent_system/` or continue agent roadmap by accident.

## Merge blockers

Block merge if any of these happen:

```text
broker/live files touched
API or UI files touched
runtime scheduler/main wiring touched
agent_system files touched
new strategy/provider/ranker logic added
expectancy/profitability/reward/label generation added
ML/ranker feature work added
backtest engine added
runtime replay executor added
export bundle contract changed without separate scope
unsafe evidence accepted successfully
unsafe replay row accepted successfully
bundle validation bypassed
PR lacks GSD and Hermes artifacts
```

## Required GSD instruction

Builder must not code until this Grill artifact is accepted.

Builder must create:

```text
docs/pr-handoffs/PR-97-gsd.md
```

The GSD artifact must list implementation choices, actual files changed, tests added, commands, and any deviation from this Grill scope.

## Required Hermes instruction

Reviewer must create after implementation:

```text
docs/pr-handoffs/PR-97-hermes.md
```

Hermes must compare the actual changed files against this Grill scope and explicitly approve, request changes, or reject.

## Final Grill verdict

Approved for a deterministic local Paper Replay Dataset Builder only.

Do not implement expectancy/profitability validation, reward/label generation, ML/ranker features, backtest execution, runtime wiring, API, UI/dashboard, broker execution, live execution, new strategies, or agent-system work in PR97.

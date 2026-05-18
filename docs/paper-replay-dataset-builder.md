# Paper Replay Dataset Builder

PR 97 adds a deterministic local paper replay dataset builder.

PR 98 hardens the replay dataset schema with an exact v1 snapshot contract.

## Purpose

PR96 packages paper evidence into a local export bundle. PR97 converts validated bundle evidence into minimal replay-ready JSONL rows. PR98 prevents the replay dataset contract from drifting silently before downstream replay, validation, or research tooling consumes it.

This is a data-shaping and schema-hardening step only. It does not compute outcomes, rewards, labels, expectancy, profitability, ML features, or trading decisions.

## Input

A validated PR96 paper export bundle:

```text
manifest.json
checksums.json
evidence/paper_evidence.jsonl
scenarios/scenario_results.json
```

## Output

Optional local JSONL file, outside the bundle root:

```text
paper_replay_dataset.jsonl
```

## Row fields

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

## Schema snapshot contract

PR98 locks the v1 dataset schema snapshot at:

```text
tests/snapshots/paper_replay_dataset_schema_v1.json
```

The snapshot freezes:

```text
schema_version
dataset_type
row_type
output_format
statuses
required_row_keys
required_result_keys
safe_flags
scope_boundary
```

Any change to row keys, result keys, safe flags, statuses, or scope boundaries must intentionally update the snapshot and explain why the v1 contract changed. Silent drift is not acceptable.

## Core operations

```text
build_paper_replay_dataset
validate_paper_replay_dataset_rows
load_paper_replay_dataset_rows
stable_replay_row_id
```

## Safety contract

Every result and row exposes:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Blocking behavior

The builder and row validator fail closed on:

```text
missing bundle root
invalid bundle
missing evidence file
corrupt evidence JSONL
non-object evidence record
unsafe evidence flags
unsafe replay rows
unknown schema version
invalid row type
missing required replay row keys
output path inside bundle root
expectancy/profitability/reward/label fields
broker/live/order-action leakage
```

## Scope boundary

This PR does not add:

```text
expectancy/profitability validation
reward/label generation
ML/ranker features
backtest execution
runtime wiring
API
UI/dashboard
broker execution
LIVE execution
new strategies
agent-system work
```

## Acceptance proof

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
# Paper Evidence Persistence Layer

PR 93 adds a minimal local JSONL persistence layer for paper evidence.

## Purpose

PR 92 produces in-memory paper pipeline evidence. PR 93 persists that evidence safely so later PRs can reset sessions, run scenarios, export bundles, create replay datasets, and validate expectancy.

This layer is not runtime execution. It does not call brokers. It does not place orders. It does not expose an API or dashboard.

## Format

```text
JSONL
```

Each line is one paper evidence record.

## Record shape

```text
schema_version
record_type
record_id
cycle_id
candidate_id
strategy_id
created_at_epoch
source
payload
payload_hash
paper_only
read_only
is_order_action
broker_api_called
real_order_id
```

`payload_hash` is deterministic and derived from canonical JSON serialization of `payload`.

## Operations

```text
write_paper_evidence_record
load_paper_evidence_records
validate_paper_evidence_record
```

## Statuses

```text
WRITTEN
LOADED
EMPTY
BLOCKED
```

## Safety contract

Write and read results expose:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

Evidence records expose the same flags.

## Blocking behavior

The persistence layer fails closed on:

```text
missing evidence path
invalid evidence path type
missing record_type
missing cycle_id
missing payload
non-object payload
unsafe payload flags
broker_api_called=true
is_order_action=true
real_order_id present
corrupt JSONL line
non-object JSONL line
payload hash mismatch
```

Missing evidence files load as safe `EMPTY` so a new paper session can start without fake failure.

## Scope boundary

This PR does not add:

```text
runtime wiring
session reset
export bundle
scenario suite
replay dataset
API
UI/dashboard
broker execution
LIVE execution
new strategies
ML/ranker work
```

## Acceptance proof

Focused:

```bash
python -m pytest tests/test_paper_evidence_persistence.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_trading_pipeline.py tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py -q
```

Additional paper truth regression if persistence imports broader contracts:

```bash
python -m pytest tests/test_paper_event_journal.py tests/test_paper_state_reducer.py tests/test_paper_event_ordering.py -q
```

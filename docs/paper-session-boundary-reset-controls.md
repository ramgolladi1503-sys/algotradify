# Paper Session Boundary and Reset Controls

PR 94 adds local paper-only session boundary records.

## Purpose

Paper evidence is now persisted as JSONL records. Without clear session boundaries, old runs can pollute new runs, scenario suites, export bundles, replay datasets, and expectancy validation.

This layer adds explicit non-destructive boundary markers.

## Boundary types

```text
SESSION_START
SESSION_END
RESET_MARKER
```

A reset marker means: isolate future interpretation from previous evidence.

A reset marker does not mean delete, truncate, rewrite, or hide history.

## Core operations

```text
build_paper_session_id
build_paper_session_boundary_record
mark_paper_session_boundary
load_paper_session_boundaries
validate_paper_session_boundary_record
```

## Record shape

```text
schema_version
record_type
session_id
boundary_type
created_at_epoch
reason
metadata
paper_only
read_only
is_order_action
broker_api_called
real_order_id
```

When persisted, the record is stored through the PR93 JSONL evidence persistence layer as:

```text
record_type=PAPER_SESSION_BOUNDARY
payload=<boundary record>
```

## Safety contract

Every result exposes:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

Boundary records expose the same safe flags.

## Blocking behavior

The boundary layer fails closed on:

```text
missing session_id
invalid boundary_type
missing created_at_epoch
non-object metadata
unsafe metadata flags
broker_api_called=true
is_order_action=true
real_order_id present
destructive reset/delete/truncate/rewrite metadata
persistence write BLOCKED
persistence load BLOCKED
```

## Scope boundary

This PR does not add:

```text
runtime wiring
destructive reset/delete/truncate
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
python -m pytest tests/test_paper_session_boundary.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_evidence_persistence.py tests/test_paper_trading_pipeline.py -q
```

Additional paper truth regression:

```bash
python -m pytest tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py -q
```

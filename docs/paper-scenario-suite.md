# Paper End-to-End Scenario Suite

PR 95 adds deterministic paper-only end-to-end scenarios.

## Purpose

The paper system now has:

```text
pipeline -> persistence -> session boundary
```

The scenario suite proves these pieces work together with controlled inputs before export bundles, replay datasets, expectancy validation, API/UI, runtime wiring, or live readiness.

## Scenario names

```text
FULL_FILL_HAPPY_PATH
PARTIAL_FILL_PATH
NO_FILL_PATH
STALE_QUOTE_BLOCKED_PATH
SESSION_RESET_MARKER_PATH
```

## Scenario flow

Each scenario can:

```text
build deterministic session id
mark SESSION_START
run paper pipeline
persist pipeline evidence
mark SESSION_END or RESET_MARKER
load persisted evidence
validate expected outcome
return PASSED / FAILED / BLOCKED
```

## Safety contract

Every scenario result exposes:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Scope boundary

This PR does not add:

```text
export bundle
replay dataset
expectancy/profitability validation
runtime wiring
API
UI/dashboard
broker execution
LIVE execution
new strategies
ML/ranker work
```

## Blocking behavior

Scenarios fail closed or fail visibly on:

```text
missing scenario name
unknown scenario name
unsafe scenario overrides
pipeline blocker
persistence write blocker
persistence load blocker
session boundary blocker
expected outcome mismatch
corrupt evidence file
```

## Acceptance proof

Focused:

```bash
python -m pytest tests/test_paper_scenarios.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_session_boundary.py tests/test_paper_evidence_persistence.py tests/test_paper_trading_pipeline.py -q
```

Additional paper truth regression:

```bash
python -m pytest tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py tests/test_paper_event_ordering.py tests/test_paper_state_reducer.py -q
```

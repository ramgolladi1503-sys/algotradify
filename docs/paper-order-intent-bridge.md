# Paper Order Intent Bridge

PR 79 adds a safe paper order intent bridge.

## Why this exists

PR 74–PR 78 built the market-data trust layer:

```text
Live Market Data Snapshot
Quote Freshness Runtime Monitor
Option Chain Depth Quality Monitor
Instrument Resolution Health Panel
Market Session / Expiry Context Guard
```

PR 79 starts the paper-trading bridge without crossing into real broker execution.

## Module

```text
paper_trading/intent_bridge.py
```

## Public exports

```python
PaperOrderIntent
PaperOrderIntentResult
build_paper_order_intent
paper_order_intent_schema_contract
validate_paper_order_intent
```

## Bridge type

```text
PAPER_ORDER_INTENT_BRIDGE
```

## Intent type

```text
PAPER_ORDER_INTENT
```

## Required safe flags

Every result and intent returns:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

## Inputs

The bridge consumes:

```text
top_executable
execution_safety
readiness
market_data
instrument_health
```

## Included snapshots

The created intent includes:

```text
candidate_snapshot
readiness_snapshot
market_data_snapshot
instrument_health_snapshot
safety_decision_snapshot
```

## Blocking conditions

The bridge blocks when:

```text
NO_SELECTED_EXECUTABLE_CANDIDATE
SELECTED_CANDIDATE_ORDER_FLAG_UNSAFE
EXECUTION_SAFETY_REQUIRED
EXECUTION_SAFETY_NOT_PERMITTED
EXECUTION_SAFETY_ORDER_FLAG_UNSAFE
READINESS_UNRESOLVED
READINESS_BLOCKED
MARKET_DATA_BLOCKED
INSTRUMENT_HEALTH_BLOCKED
CANDIDATE_ID_REQUIRED
```

It also blocks unsafe snapshot flags:

```text
*_ORDER_FLAG_UNSAFE
*_BROKER_API_CALLED
*_REAL_ORDER_ID_PRESENT
```

## Degraded-but-allowed conditions

Warnings do not block paper intent creation:

```text
READINESS_FALLBACK_USED
MARKET_DATA_DEGRADED
INSTRUMENT_HEALTH_DEGRADED
```

## Test coverage

`tests/test_dry_run_execution_adapter.py` covers:

```text
schema contract safe flags
valid paper intent creation
missing selected candidate block
safety-not-permitted block
bad market context block
unresolved instrument health block
degraded context warnings while still creating paper intent
safe flags on result and intent
```

## Scope boundary

This PR does not add real broker execution, LIVE orders, UI rendering, order lifecycle simulation, fills, PnL, or slippage. It only creates a safe paper-order intent contract.

## Next logical PR

```text
PR 80 — Paper Broker Order Lifecycle
```

That PR should model paper order lifecycle states without real broker calls.

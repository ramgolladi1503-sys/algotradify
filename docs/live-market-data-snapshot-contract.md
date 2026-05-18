# Live Market Data Snapshot Contract

PR 74 adds a read-only live market data snapshot contract.

## Why this exists

The movement opportunity pipeline and dashboard are now stable enough to demo, but ranking signals are only useful if the market data feeding them is trustworthy.

This contract creates a single normalized snapshot for live market-data quality before deeper runtime monitors are built.

## Module

```text
market_readiness/live_snapshot.py
```

## Public exports

```python
LiveMarketDataSnapshot
LiveMarketDataSnapshotStatus
build_live_market_data_snapshot
live_market_data_snapshot_schema_contract
```

## Snapshot type

```text
LIVE_MARKET_DATA_SNAPSHOT
```

## Required safe flags

Every snapshot returns:

```text
read_only=true
is_order_action=false
```

## Captured fields

Top-level fields include:

```text
schema_version
snapshot_type
symbol
status
read_only
is_order_action
source
session_state
spot
option_chain
spot_quote_fresh
option_chain_fresh
source_reliable
session_open
blockers
warnings
```

Spot fields:

```text
ltp
quote_age_sec
max_quote_age_sec
```

Option-chain fields:

```text
age_sec
max_age_sec
expiry
ce_count
pe_count
```

## Statuses

```text
READY
BLOCKED_MISSING_SPOT
BLOCKED_STALE_SPOT
BLOCKED_FALLBACK_SOURCE
BLOCKED_MISSING_OPTION_CHAIN
BLOCKED_STALE_OPTION_CHAIN
BLOCKED_SESSION_CLOSED
```

## Default thresholds

```text
max_spot_quote_age_sec=2.0
max_option_chain_age_sec=5.0
```

## Test coverage

`tests/test_market_readiness.py` covers:

```text
schema contract completeness
valid fresh primary open-session snapshot
stale spot quote
missing spot price
fallback/unreliable source
missing option chain
stale option chain
closed session
zero option-side warning
safe flags on every snapshot
```

## Scope boundary

This PR does not add UI, providers, broker behavior, runtime ranking changes, or execution behavior. It only defines the normalized market data quality snapshot contract.

## Next logical PR

```text
PR 75 — Quote Freshness Runtime Monitor
```

That PR should consume this snapshot contract and apply runtime monitoring around quote age/freshness.

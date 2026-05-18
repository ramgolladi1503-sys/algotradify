# Quote Freshness Runtime Monitor

PR 75 adds a read-only runtime monitor on top of the Live Market Data Snapshot contract from PR 74.

## Why this exists

PR 74 normalized live market-data quality into `LIVE_MARKET_DATA_SNAPSHOT`.

PR 75 aggregates those snapshots into a runtime monitor so the system can quickly tell whether market data is healthy, degraded, blocked, or empty before downstream ranking depends on it.

## Module

```text
market_readiness/quote_freshness_monitor.py
```

## Public exports

```python
QuoteFreshnessMonitorStatus
QuoteFreshnessRuntimeMonitor
build_quote_freshness_runtime_monitor
quote_freshness_runtime_monitor_schema_contract
```

## Monitor type

```text
QUOTE_FRESHNESS_RUNTIME_MONITOR
```

## Required safe flags

Every monitor output returns:

```text
read_only=true
is_order_action=false
```

## Monitor statuses

```text
HEALTHY
DEGRADED
BLOCKED
EMPTY
```

## Summary fields

```text
snapshot_count
ready_count
stale_spot_count
missing_spot_count
fallback_source_count
missing_option_chain_count
stale_option_chain_count
closed_session_count
blocked_count
warning_count
fresh_ratio
read_only
is_order_action
```

## Blocker mapping

The monitor emits blockers when it sees bad snapshot states:

```text
NO_MARKET_DATA_SNAPSHOTS
MISSING_SPOT_DATA_PRESENT
STALE_SPOT_QUOTES_PRESENT
FALLBACK_MARKET_DATA_SOURCE_PRESENT
MISSING_OPTION_CHAIN_PRESENT
STALE_OPTION_CHAIN_PRESENT
MARKET_SESSION_CLOSED_PRESENT
```

## Warning mapping

Snapshot warnings are lifted into monitor warnings:

```text
SNAPSHOT_WARNINGS_PRESENT
<symbol>:<snapshot-warning>
```

## Test coverage

`tests/test_market_readiness.py` covers:

```text
schema contract completeness
healthy monitor for all fresh snapshots
blocked monitor for stale spot quotes
blocked monitor for missing spot data
blocked monitor for fallback source
blocked monitor for closed session
blocked monitor for missing and stale option chain
empty monitor when no snapshots exist
degraded monitor for warning-only snapshots
prebuilt snapshot support
safe flags on monitor and snapshots
```

## Scope boundary

This PR does not add UI, providers, broker behavior, ranking changes, or execution behavior. It only adds a read-only runtime monitor contract for quote freshness and market-data quality.

## Next logical PR

```text
PR 76 — Option Chain Depth Quality Monitor
```

That PR should focus on option-chain depth/side quality instead of general freshness.

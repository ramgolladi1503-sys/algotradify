# Option Chain Depth Quality Monitor

PR 76 adds a read-only option-chain depth quality monitor.

## Why this exists

PR 74 added the live market data snapshot contract.
PR 75 added the quote freshness runtime monitor.

Fresh quotes are not enough. Option movement signals can still be fake if CE/PE depth is one-sided, zero, shallow, stale, or badly imbalanced.

## Module

```text
market_readiness/option_chain_depth_monitor.py
```

## Public exports

```python
OptionChainDepthQualityMonitor
OptionChainDepthQualityStatus
build_option_chain_depth_quality_monitor
option_chain_depth_quality_schema_contract
```

## Monitor type

```text
OPTION_CHAIN_DEPTH_QUALITY_MONITOR
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
BLOCKED_MISSING_SIDE
BLOCKED_ZERO_SIDE
BLOCKED_SHALLOW_DEPTH
BLOCKED_STALE_DEPTH
BLOCKED_DEPTH_IMBALANCE
EMPTY
```

## Summary fields

```text
ce_count
pe_count
ce_depth
pe_depth
total_depth
depth_age_sec
min_side_count
min_total_depth
max_depth_age_sec
max_imbalance_ratio
imbalance_ratio
missing_side_count
zero_side_count
shallow_depth_count
stale_depth_count
imbalance_count
read_only
is_order_action
```

## Side quality fields

```text
ce_available
pe_available
ce_depth_ok
pe_depth_ok
depth_fresh
imbalance_ok
```

## Default thresholds

```text
min_side_count=1
min_total_depth=100.0
max_depth_age_sec=5.0
max_imbalance_ratio=3.0
```

## Blockers

```text
NO_OPTION_CHAIN_DEPTH_DATA
MISSING_CE_SIDE_COUNT
MISSING_PE_SIDE_COUNT
ZERO_CE_SIDE_COUNT
ZERO_PE_SIDE_COUNT
MISSING_CE_DEPTH
MISSING_PE_DEPTH
ZERO_CE_DEPTH
ZERO_PE_DEPTH
TOTAL_DEPTH_BELOW_MINIMUM
MISSING_DEPTH_AGE
STALE_OPTION_DEPTH
OPTION_DEPTH_IMBALANCE
```

## Warnings

```text
DEPTH_IMBALANCE_UNAVAILABLE
```

## Test coverage

`tests/test_market_readiness.py` covers:

```text
schema contract completeness
healthy balanced fresh depth
missing CE/PE side state
zero-side state
shallow total-depth state
stale depth state
depth imbalance state
empty/no-depth state
imbalance unavailable warning
safe flags on monitor output
```

## Scope boundary

This PR does not add UI, providers, broker behavior, ranking changes, or execution behavior. It only adds a read-only option-chain depth quality monitor contract.

## Next logical PR

```text
PR 77 — Instrument Resolution Health Panel
```

That PR should expose instrument resolution health after data quality contracts are stable.

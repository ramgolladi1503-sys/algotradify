# Instrument Resolution Health Panel

PR 77 adds a read-only instrument resolution health contract/panel payload.

## Why this exists

The repo already has broker contract readiness and option contract resolution. This PR does not replace that resolver.

Instead, it summarizes existing broker contract readiness records into a dashboard-consumable health payload so unresolved, fallback, missing-token, and mismatched instruments are visible before any downstream decision layer depends on them.

## Module

```text
broker_contract/instrument_resolution_health.py
```

## Public exports

```python
InstrumentResolutionHealthPanel
InstrumentResolutionHealthStatus
build_instrument_resolution_health_panel
instrument_resolution_health_schema_contract
```

## Panel type

```text
INSTRUMENT_RESOLUTION_HEALTH_PANEL
```

## Required safe flags

Every panel output returns:

```text
read_only=true
is_order_action=false
```

Every row also returns:

```text
read_only=true
is_order_action=false
```

## Panel statuses

```text
HEALTHY
DEGRADED_FALLBACK
BLOCKED_UNRESOLVED
EMPTY
```

## Summary fields

```text
record_count
resolved_count
unresolved_count
exact_count
fallback_count
missing_token_count
expired_or_mismatched_count
blocked_count
warning_count
read_only
is_order_action
```

## Row fields

```text
candidate_id
symbol
strategy_id
readiness_status
resolved
instrument_token
fallback_used
fallback_distance
resolution_source
tradingsymbol
expiry
strike
option_type
exchange
blockers
warnings
read_only
is_order_action
```

## Blockers

Panel-level blockers:

```text
NO_INSTRUMENT_RESOLUTION_RECORDS
UNRESOLVED_INSTRUMENTS_PRESENT
MISSING_INSTRUMENT_TOKENS_PRESENT
EXPIRED_OR_MISMATCHED_INSTRUMENTS_PRESENT
```

Row-level mismatch blockers:

```text
INSTRUMENT_MISMATCH_EXPIRY
INSTRUMENT_MISMATCH_STRIKE
INSTRUMENT_MISMATCH_OPTION_TYPE
INSTRUMENT_MISMATCH_EXCHANGE
```

## Warnings

```text
FALLBACK_INSTRUMENT_RESOLUTION_PRESENT
ROW_WARNINGS_PRESENT
<candidate_id>:<row-warning>
```

## Test coverage

`tests/test_broker_contract_readiness.py` covers:

```text
schema contract completeness
healthy exact match
fallback match degradation
missing token block
missing request block
expired/mismatched instrument block
empty safe state
safe flags on panel and rows
```

## Scope boundary

This PR does not add UI rendering, broker behavior, order behavior, movement providers, or ranking changes. It only adds a read-only health contract over existing broker-contract readiness outputs.

## Next logical PR

```text
PR 78 — Market Session/Expiry Context Guard
```

That PR should ensure market session and expiry context are validated before movement opportunities are trusted.

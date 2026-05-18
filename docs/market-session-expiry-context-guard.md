# Market Session / Expiry Context Guard

PR 78 adds a read-only market session and expiry context guard.

## Why this exists

The movement dashboard/API and live market-data quality contracts are now stable. The next failure mode is context: a movement opportunity can look valid while the market is pre-open, closing, closed, or the selected contract expiry is invalid/expired.

This guard blocks stale or invalid session/expiry context before downstream ranking trusts it.

## Module

```text
market_readiness/session_expiry_guard.py
```

## Public exports

```python
MarketSessionExpiryGuard
MarketSessionExpiryGuardStatus
build_market_session_expiry_guard
market_session_expiry_guard_schema_contract
```

## Guard type

```text
MARKET_SESSION_EXPIRY_CONTEXT_GUARD
```

## Required safe flags

Every guard output returns:

```text
read_only=true
is_order_action=false
```

## Guard statuses

```text
READY
DEGRADED_NEAR_EXPIRY
BLOCKED_PRE_OPEN
BLOCKED_CLOSING
BLOCKED_CLOSED
BLOCKED_EXPIRED_CONTRACT
BLOCKED_INVALID_EXPIRY
BLOCKED_MISSING_CONTEXT
```

## Top-level fields

```text
schema_version
guard_type
status
read_only
is_order_action
session_state
expiry
expiry_type
trade_date
days_to_expiry
session_open
expiry_valid
contract_expired
near_expiry
blockers
warnings
```

## Session states

Open states:

```text
OPEN
LIVE
REGULAR
```

Blocked pre-open states:

```text
PRE_OPEN
PREOPEN
```

Blocked closing states:

```text
CLOSING
CLOSE_AUCTION
```

Blocked closed states:

```text
CLOSED
HOLIDAY
POST_CLOSE
POSTCLOSE
```

## Expiry behavior

The guard validates:

```text
expiry date parseability
days_to_expiry
expired contract
near-expiry warning
expiry type: WEEKLY / MONTHLY / UNKNOWN
```

Near expiry is degraded, not blocked by default:

```text
near_expiry_days=1
```

## Blockers

```text
MISSING_MARKET_SESSION_STATE
MARKET_SESSION_PRE_OPEN
MARKET_SESSION_CLOSING
MARKET_SESSION_CLOSED
UNKNOWN_MARKET_SESSION_STATE
MISSING_EXPIRY
INVALID_EXPIRY
EXPIRED_CONTRACT
```

## Warnings

```text
NEAR_EXPIRY_CONTRACT
EXPIRY_TYPE_UNKNOWN
```

## Test coverage

`tests/test_market_readiness.py` covers:

```text
schema contract completeness
open valid future expiry
pre-open session block
closing session block
closed session block
expired contract block
invalid expiry block
missing context block
near-expiry degraded state
unknown expiry type warning
safe flags on every guard output
```

## Scope boundary

This PR does not add UI, providers, broker behavior, ranking changes, or execution behavior. It only adds a read-only context guard for market session and expiry validity.

## Next logical PR

```text
PR 79 — Paper Order Intent Bridge
```

That PR should start the safe paper-trading bridge only after market data, option depth, instrument resolution, and session/expiry context are guarded.

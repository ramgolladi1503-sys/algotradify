# Read-only Movement Opportunity API

PR 68 added a read-only API contract around the movement opportunity pipeline from PR 67.
PR 69 hardens that contract so future API/dashboard work cannot silently remove keys or unsafe flags.

## Files

```text
api/movement_opportunity_route.py
api/server_with_movement.py
tests/test_movement_opportunity_api.py
docs/movement-opportunity-api.md
```

## Routes

```text
GET /movement-opportunity
GET /movement-opportunity/schema
```

The route is mounted through:

```python
install_movement_opportunity_route(app)
```

A dedicated adapter is available:

```text
api/server_with_movement.py
```

## Required query parameters

```text
symbol
ts_epoch
```

## Optional context query parameters

```text
spot_ltp
vwap
day_high
day_low
orb_high
orb_low
prev_day_high
prev_day_low
atr
atr_short
atr_long
range_width_pct
volume_z
volatility_state
regime_hint
option_ce_ltp
option_pe_ltp
ce_premium_change
pe_premium_change
ce_spread_pct
pe_spread_pct
ce_depth
pe_depth
option_ltp_age_sec
quote_source
time_of_day
minutes_since_open
minutes_to_close
expiry_context
```

## Frozen top-level response fields

The `/movement-opportunity` response must keep these top-level fields in order:

```text
api_schema_version
route
method
read_only
is_order_action
context
summary
ranked_candidates
rank_records
exclusions
warnings
diagnostics
pipeline
```

PR 69 adds tests that fail if these top-level keys disappear or are reordered.

## Nested schema contract

The schema endpoint now declares required nested keys for:

```text
context
summary
ranked_candidates[]
rank_records[]
exclusions[]
diagnostics[]
pipeline
pipeline.summary
pipeline.rank_result
```

The endpoint tests validate the real response against those declarations.

## Required safety flags

The public API contract requires:

```text
top_level.read_only=true
top_level.is_order_action=false
context.is_order_action=false
summary.read_only=true
summary.is_order_action=false
ranked_candidates[].is_order_action=false
rank_records[].is_order_action=false
exclusions[].is_order_action=false
diagnostics[].is_order_action=false
pipeline.read_only=true
pipeline.is_order_action=false
pipeline.summary.read_only=true
pipeline.summary.is_order_action=false
pipeline.rank_result.is_order_action=false
```

Pipeline internals must also keep safe flags on option-enriched candidates, no-trade-filter candidates, no-trade-filter results, and diagnostics.

## OpenAPI contract

The OpenAPI contract must expose only GET routes:

```text
GET /movement-opportunity
GET /movement-opportunity/schema
```

Required OpenAPI query params:

```text
symbol
ts_epoch
```

No dashboard screen is added in PR 69.

## Contract tests

The tests prove:

```text
schema contract is read-only
schema declares frozen top-level keys
schema declares nested required keys
query parameters build StrategyContext safely
endpoint returns pipeline payload
endpoint top-level keys cannot disappear
endpoint nested keys cannot disappear
ranked candidates keep required candidate keys
rank records keep required rank keys
fallback quote blocks ranking
blocked candidates surface as safe rank exclusions
missing required params return 422
installer is idempotent
OpenAPI exposes only GET routes
server_with_movement mounts the route
```

## Validation

```bash
python -m pytest tests/test_movement_opportunity_api.py -q
python -m pytest tests/test_movement_pipeline.py tests/test_movement_ranker.py tests/test_no_trade_filter.py -q
```

## Honest limitation

This freezes the API contract before UI/dashboard work. It remains a read-only evidence surface.

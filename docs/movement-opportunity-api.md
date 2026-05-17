# Read-only Movement Opportunity API

PR 68 adds a read-only API contract around the movement opportunity pipeline from PR 67.

## Files

```text
api/movement_opportunity_route.py
api/server_with_movement.py
tests/test_movement_opportunity_api.py
docs/movement-opportunity-api.md
```

## Route

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

## Response shape

Top-level response fields:

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

The `pipeline` field contains the full `MovementOpportunityPipelineResult` payload.

## Safety boundary

The endpoint is read-only:

```text
read_only=true
is_order_action=false
```

It does not add dashboard screens, broker integration, order intent integration, or execution behavior.

## Contract tests

The tests prove:

```text
schema contract is read-only
query parameters build StrategyContext safely
endpoint returns pipeline payload
fallback quote blocks ranking
missing required params return 422
installer is idempotent
server_with_movement mounts the route
```

## Validation

```bash
python -m pytest tests/test_movement_opportunity_api.py -q
python -m pytest tests/test_movement_pipeline.py tests/test_movement_ranker.py tests/test_no_trade_filter.py -q
```

## Honest limitation

This is an API wrapper around read-only opportunities. It still does not choose trades. The next correct step is a UI/API consumer or contract dashboard panel, not direct execution.

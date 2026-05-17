# Compression Breakout and Trend Pullback Providers

PR 62 adds two movement strategy providers:

```text
COMPRESSION_BREAKOUT
TREND_PULLBACK
```

These are provider-level candidate producers only. They do not rank candidates, create order intents, call brokers, submit orders, modify orders, cancel orders, exit positions, expose API routes, or change dashboard behavior.

## Files

```text
movement_engine/providers/compression_trend.py
tests/test_compression_trend_providers.py
docs/compression-breakout-trend-pullback.md
```

## Provider contract

Each provider accepts `StrategyContext` and returns `list[StrategyCandidate]`.

The providers must:

- return movement candidates only
- preserve evidence
- keep `is_order_action=false`
- register through `MovementStrategyRegistry`
- feed into `build_candidate_pool(...)`
- rely on the existing candidate pool for hard-block conversion

The providers must not:

- import broker/order/API/dashboard modules
- build `OrderIntent`
- call `PaperBroker`
- call live broker clients
- expose execution controls
- mark anything as executable

## Compression Breakout

`compression_breakout_provider(...)` looks for a compressed market resolving beyond the current day range boundary.

Bullish candidate shape:

```text
compression evidence exists
volume_z >= 1.0
spot_ltp > day_high
candidate direction = BUY_CALL
movement_type = COMPRESSION_BREAKOUT
```

Bearish candidate shape:

```text
compression evidence exists
volume_z >= 1.0
spot_ltp < day_low
candidate direction = BUY_PUT
movement_type = COMPRESSION_BREAKOUT
```

Compression evidence can come from:

```text
range_width_pct <= 0.45
atr_short / atr_long <= 0.85
volatility_state = COMPRESSION
regime_hint = COMPRESSION
```

If the setup is not triggered, the provider still returns a diagnostic candidate proposal with blocker:

```text
COMPRESSION_BREAKOUT_NOT_TRIGGERED
```

## Trend Pullback

`trend_pullback_provider(...)` looks for a continuation pullback around VWAP or day-range structure.

Bullish candidate shape:

```text
regime_hint = TREND_UP or bullish range/VWAP structure
spot_ltp near or above vwap
CE premium confirms over PE premium
candidate direction = BUY_CALL
movement_type = TREND_PULLBACK_CONTINUATION
```

Bearish candidate shape:

```text
regime_hint = TREND_DOWN or bearish range/VWAP structure
spot_ltp near or below vwap
PE premium confirms over CE premium
candidate direction = BUY_PUT
movement_type = TREND_PULLBACK_CONTINUATION
```

If the setup is not triggered, the provider returns a diagnostic candidate proposal with blocker:

```text
TREND_PULLBACK_NOT_TRIGGERED
```

## Evidence preserved

The providers attach evidence such as:

```text
symbol
ts_epoch
spot_ltp
vwap
day_high
day_low
range_width_pct
atr_short
atr_long
regime_hint
volatility_state
option_ltp_age_sec
quote_source
ce_spread_pct
pe_spread_pct
ce_depth
pe_depth
provider
strategy_family
```

All evidence remains read-only and non-execution.

## Hard blockers

The providers surface existing candidate-pool hard blockers:

```text
STALE_OPTION_LTP
WIDE_SPREAD
MISSING_DEPTH
FALLBACK_QUOTE_ONLY
UNRESOLVED_CONTRACT
CONFLICTING_TRAP_SIGNAL
NO_TRADE_CHOP
MARKET_CLOSED
```

The provider output remains a raw candidate proposal. The candidate pool owns conversion to `BLOCKED_CANDIDATE`.

Example:

```text
COMPRESSION_BREAKOUT candidate + WIDE_SPREAD
-> provider emits RAW_CANDIDATE with blocker WIDE_SPREAD
-> candidate pool converts to BLOCKED_CANDIDATE
```

## Registry integration

Use:

```python
from movement_engine import MovementStrategyRegistry, register_compression_trend_providers

registry = register_compression_trend_providers(MovementStrategyRegistry())
registry_result = registry.run(context)
```

The helper `build_compression_trend_candidate_pool(context)` proves the intended safe path:

```text
StrategyContext
-> MovementStrategyRegistry
-> COMPRESSION_BREAKOUT / TREND_PULLBACK providers
-> build_candidate_pool(...)
-> CandidatePoolResult
```

## Validation

Focused validation:

```bash
python -m pytest tests/test_compression_trend_providers.py -q
python -m pytest tests/test_opening_drive_orb_providers.py tests/test_candidate_pool.py tests/test_movement_registry.py -q
```

Safety validation:

```bash
python -m pytest tests/test_order_intent_contract.py tests/test_paper_broker_adapter.py tests/test_execution_safety.py -q
```

## Honest limitation

These providers are deliberately basic. They are not a complete trading system and do not prove profitability. They only prove that compression breakout and trend pullback setups can produce contract-safe, evidence-rich, non-execution candidates.

The next correct layers remain option-pressure confirmation, no-trade logic, ranking, and read-only evidence/API surfaces before any execution path is touched.

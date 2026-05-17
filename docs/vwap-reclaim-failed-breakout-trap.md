# VWAP Reclaim and Failed Breakout Trap Providers

PR 63 adds two movement strategy providers:

```text
VWAP_RECLAIM
FAILED_BREAKOUT_TRAP
```

These are provider-level candidate producers only. They do not rank candidates, create order intents, call brokers, submit orders, modify orders, cancel orders, exit positions, expose API routes, or change dashboard behavior.

## Files

```text
movement_engine/providers/vwap_trap.py
tests/test_vwap_trap_providers.py
docs/vwap-reclaim-failed-breakout-trap.md
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

## VWAP Reclaim

`vwap_reclaim_provider(...)` looks for a VWAP reclaim or VWAP loss with option premium confirmation.

Bullish candidate shape:

```text
spot_ltp near VWAP
spot_ltp >= vwap
CE premium confirms over PE premium
candidate direction = BUY_CALL
movement_type = VWAP_RECLAIM
```

Bearish candidate shape:

```text
spot_ltp near VWAP
spot_ltp <= vwap
PE premium confirms over CE premium
candidate direction = BUY_PUT
movement_type = VWAP_RECLAIM
```

If the setup is not triggered, the provider still returns a diagnostic candidate proposal with blocker:

```text
VWAP_RECLAIM_NOT_TRIGGERED
```

## Failed Breakout Trap

`failed_breakout_trap_provider(...)` looks for failed attempts around day, ORB, or previous-day range boundaries.

Upper-boundary failure shape:

```text
spot_ltp near upper boundary
CE premium stalls or weakens
PE premium expands
candidate direction = BUY_PUT
movement_type = FAILED_BREAKOUT_TRAP
```

Lower-boundary failure shape:

```text
spot_ltp near lower boundary
PE premium stalls or weakens
CE premium expands
candidate direction = BUY_CALL
movement_type = FAILED_BREAKOUT_TRAP
```

If the setup is not triggered, the provider returns a diagnostic candidate proposal with blocker:

```text
FAILED_BREAKOUT_TRAP_NOT_TRIGGERED
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
orb_high
orb_low
prev_day_high
prev_day_low
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
NO_TRADE_CHOP
MARKET_CLOSED
```

The provider output remains a raw candidate proposal. The candidate pool owns conversion to `BLOCKED_CANDIDATE`.

Example:

```text
VWAP_RECLAIM candidate + FALLBACK_QUOTE_ONLY
-> provider emits RAW_CANDIDATE with blocker FALLBACK_QUOTE_ONLY
-> candidate pool converts to BLOCKED_CANDIDATE
```

## Registry integration

Use:

```python
from movement_engine import MovementStrategyRegistry, register_vwap_trap_providers

registry = register_vwap_trap_providers(MovementStrategyRegistry())
registry_result = registry.run(context)
```

The helper `build_vwap_trap_candidate_pool(context)` proves the intended safe path:

```text
StrategyContext
-> MovementStrategyRegistry
-> VWAP_RECLAIM / FAILED_BREAKOUT_TRAP providers
-> build_candidate_pool(...)
-> CandidatePoolResult
```

## Validation

Focused validation:

```bash
python -m pytest tests/test_vwap_trap_providers.py -q
python -m pytest tests/test_compression_trend_providers.py tests/test_opening_drive_orb_providers.py tests/test_candidate_pool.py tests/test_movement_registry.py -q
```

Safety validation:

```bash
python -m pytest tests/test_order_intent_contract.py tests/test_paper_broker_adapter.py tests/test_execution_safety.py -q
```

## Honest limitation

These providers are deliberately basic. They are not a complete trading system and do not prove profitability. They only prove that VWAP reclaim and failed-breakout trap setups can produce contract-safe, evidence-rich, non-execution candidates.

After this PR, adding more raw providers without confirmation and no-trade layers would create noise. The next correct move is option-pressure confirmation, then no-trade logic, then ranking.

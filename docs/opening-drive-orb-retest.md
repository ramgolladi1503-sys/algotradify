# Opening Drive and ORB Retest Providers

PR 61 adds the first two movement strategy providers:

```text
OPENING_DRIVE
ORB_RETEST
```

These are provider-level candidate producers only. They do not rank candidates, create order intents, call brokers, submit orders, modify orders, cancel orders, exit positions, expose API routes, or change dashboard behavior.

## Files

```text
movement_engine/providers/__init__.py
movement_engine/providers/opening_drive_orb.py
tests/test_opening_drive_orb_providers.py
docs/opening-drive-orb-retest.md
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

## Opening Drive

`opening_drive_provider(...)` looks for a basic opening-range breakout with early volume expansion.

Bullish candidate shape:

```text
spot_ltp > orb_high
volume_z >= 0.8
candidate direction = BUY_CALL
movement_type = OPENING_MOMENTUM_EXPANSION
```

Bearish candidate shape:

```text
spot_ltp < orb_low
volume_z >= 0.8
candidate direction = BUY_PUT
movement_type = OPENING_MOMENTUM_EXPANSION
```

If the opening drive is not triggered, the provider still returns a diagnostic candidate proposal with blocker:

```text
OPENING_DRIVE_NOT_TRIGGERED
```

That is useful because the operator can see why a setup did not qualify instead of seeing a silent empty list.

## ORB Retest

`orb_retest_provider(...)` looks for a basic opening-range breakout retest holding near the broken opening-range boundary.

Bullish retest shape:

```text
spot_ltp near orb_high
spot_ltp >= vwap
CE premium change >= PE premium change
candidate direction = BUY_CALL
movement_type = ORB_BREAKOUT_RETEST
```

Bearish retest shape:

```text
spot_ltp near orb_low
spot_ltp <= vwap
PE premium change >= CE premium change
candidate direction = BUY_PUT
movement_type = ORB_BREAKOUT_RETEST
```

If the ORB retest is not triggered, the provider returns a diagnostic candidate proposal with blocker:

```text
ORB_RETEST_NOT_TRIGGERED
```

## Evidence preserved

The providers attach evidence such as:

```text
symbol
ts_epoch
spot_ltp
vwap
orb_high
orb_low
regime_hint
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

The providers surface hard blockers that the PR 60 candidate pool already knows how to enforce:

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
OPENING_DRIVE candidate + WIDE_SPREAD
-> provider emits RAW_CANDIDATE with blocker WIDE_SPREAD
-> candidate pool converts to BLOCKED_CANDIDATE
```

## Registry integration

Use:

```python
from movement_engine import MovementStrategyRegistry, register_opening_drive_orb_providers

registry = register_opening_drive_orb_providers(MovementStrategyRegistry())
registry_result = registry.run(context)
```

The helper `build_opening_drive_orb_candidate_pool(context)` proves the intended safe path:

```text
StrategyContext
-> MovementStrategyRegistry
-> OPENING_DRIVE / ORB_RETEST providers
-> build_candidate_pool(...)
-> CandidatePoolResult
```

## Validation

Focused validation:

```bash
python -m pytest tests/test_opening_drive_orb_providers.py -q
python -m pytest tests/test_movement_registry.py tests/test_candidate_pool.py -q
```

Safety validation:

```bash
python -m pytest tests/test_order_intent_contract.py tests/test_paper_broker_adapter.py tests/test_execution_safety.py -q
```

## Honest limitation

These providers are intentionally simple. They are not a complete trading system and they do not prove profitability. They only prove the first two movement setups can produce contract-safe, evidence-rich, non-execution candidates.

The next mistake to avoid is obvious: do not jump from these raw candidates to execution. The correct next layers are confirmation, no-trade logic, ranking, and read-only evidence/API surfaces before any execution path is touched.

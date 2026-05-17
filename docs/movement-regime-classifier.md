# Movement Regime Classifier

PR 59 adds deterministic movement-regime classification for the movement opportunity engine.

## Purpose

The classifier reads `StrategyContext` and emits regime scores. It does not emit trades, candidates, order intents, or execution actions.

## Implementation

```text
movement_engine/regime.py
```

Exports:

```text
MovementRegime
MovementRegimeResult
classify_movement_regime
```

## Supported regimes

```text
TREND_UP
TREND_DOWN
RANGE
CHOP
COMPRESSION
VOLATILITY_EXPANSION
TRAP_RISK
EXHAUSTION_RISK
INCONCLUSIVE
```

## Output shape

```json
{
  "primary_regime": "COMPRESSION",
  "scores": {
    "TREND_UP": 0.0,
    "TREND_DOWN": 0.0,
    "RANGE": 0.1,
    "CHOP": 0.0,
    "COMPRESSION": 0.8,
    "VOLATILITY_EXPANSION": 0.0,
    "TRAP_RISK": 0.0,
    "EXHAUSTION_RISK": 0.0,
    "INCONCLUSIVE": 0.0
  },
  "warnings": [],
  "blockers": [],
  "evidence": {},
  "is_order_action": false
}
```

## Missing data behavior

Missing critical data must not crash.

Examples:

```text
missing context -> INCONCLUSIVE
missing spot_ltp -> INCONCLUSIVE + SPOT_LTP_MISSING
missing vwap -> INCONCLUSIVE + VWAP_MISSING
```

## Signals used

The v1 classifier uses deterministic scoring from:

```text
spot vs VWAP
position within day range
CE/PE premium change bias
range width percent
ATR short vs ATR long ratio
volume z-score
manual regime hint
volatility state hint
```

## Safety boundary

This PR does not add:

- movement strategies
- candidate pool
- opportunity ranker
- execution integration
- broker integration
- order integration
- dashboard changes

The classifier always returns `is_order_action=false`.

## Tests

Added:

```text
tests/test_movement_regime.py
```

The tests prove:

- missing context returns INCONCLUSIVE
- missing spot/vwap returns INCONCLUSIVE
- trend up detection
- trend down detection
- range detection
- chop detection
- compression detection
- volatility expansion detection
- trap risk detection
- exhaustion risk detection
- regime hint remains non-execution behavior

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from strategies.base import StrategyCandidateDraft, StrategyContext


def _feature_number(features: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = features.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ThresholdStrategy:
    """Small deterministic adapter used to standardize strategy outputs.

    This is intentionally not a trading edge. It is a contract adapter that
    proves strategies emit candidate drafts with stable identity and provenance.
    Real strategy internals can be wired behind this contract later.
    """

    strategy_id: str
    setup_family: str
    display_name: str
    trigger_feature: str
    direction: str
    trigger_threshold: float
    required_market_regime: str | None = None
    required_data: tuple[str, ...] = ()

    def generate(self, context: StrategyContext) -> list[StrategyCandidateDraft]:
        value = _feature_number(context.features, self.trigger_feature)
        if value < self.trigger_threshold:
            return []

        confidence = max(0.0, min(100.0, value))
        candidate_id = f"{self.strategy_id}:{context.symbol}:{context.timestamp_epoch or 'na'}"
        return [
            StrategyCandidateDraft(
                candidate_id=candidate_id,
                symbol=context.symbol,
                strategy_id=self.strategy_id,
                setup_family=self.setup_family,
                direction=self.direction,
                confidence=confidence,
                entry_hypothesis={
                    "type": "strategy_signal_hypothesis",
                    "trigger_feature": self.trigger_feature,
                    "trigger_value": value,
                },
                invalidation_hypothesis={
                    "type": "feature_threshold_invalidation",
                    "feature": self.trigger_feature,
                    "invalid_below": self.trigger_threshold,
                },
                required_market_regime=self.required_market_regime,
                required_data=list(self.required_data),
                signal_features={self.trigger_feature: value},
                provenance={
                    "source": "strategies.simple_signal.ThresholdStrategy",
                    "strategy_id": self.strategy_id,
                },
                raw={"context": context.raw},
            )
        ]


class OrbRetestStrategy(ThresholdStrategy):
    def __init__(self) -> None:
        super().__init__(
            strategy_id="orb_retest",
            setup_family="ORB_RETEST",
            display_name="Opening Range Breakout Retest",
            trigger_feature="orb_retest_score",
            direction="BULLISH",
            trigger_threshold=70,
            required_market_regime="TRENDING",
            required_data=("index_ltp", "opening_range", "volume", "quote"),
        )


class VwapReclaimStrategy(ThresholdStrategy):
    def __init__(self) -> None:
        super().__init__(
            strategy_id="vwap_reclaim",
            setup_family="VWAP_RECLAIM",
            display_name="VWAP Reclaim",
            trigger_feature="vwap_reclaim_score",
            direction="BULLISH",
            trigger_threshold=68,
            required_market_regime="TRENDING",
            required_data=("index_ltp", "vwap", "volume", "quote"),
        )


class TrendPullbackStrategy(ThresholdStrategy):
    def __init__(self) -> None:
        super().__init__(
            strategy_id="trend_pullback",
            setup_family="TREND_PULLBACK",
            display_name="Trend Pullback Continuation",
            trigger_feature="trend_pullback_score",
            direction="BULLISH",
            trigger_threshold=65,
            required_market_regime="TRENDING",
            required_data=("trend", "pullback_depth", "quote"),
        )


class FailedBreakoutReversalStrategy(ThresholdStrategy):
    def __init__(self) -> None:
        super().__init__(
            strategy_id="failed_breakout_reversal",
            setup_family="FAILED_BREAKOUT_REVERSAL",
            display_name="Failed Breakout Reversal",
            trigger_feature="failed_breakout_reversal_score",
            direction="BEARISH",
            trigger_threshold=72,
            required_market_regime="REVERSAL",
            required_data=("breakout_level", "rejection", "quote"),
        )


class RangeReversionStrategy(ThresholdStrategy):
    def __init__(self) -> None:
        super().__init__(
            strategy_id="range_reversion",
            setup_family="RANGE_REVERSION",
            display_name="Range Reversion",
            trigger_feature="range_reversion_score",
            direction="NEUTRAL",
            trigger_threshold=66,
            required_market_regime="RANGE",
            required_data=("range_high", "range_low", "quote"),
        )


class ExpiryMomentumStrategy(ThresholdStrategy):
    def __init__(self) -> None:
        super().__init__(
            strategy_id="expiry_momentum",
            setup_family="EXPIRY_MOMENTUM",
            display_name="Expiry Momentum",
            trigger_feature="expiry_momentum_score",
            direction="BULLISH",
            trigger_threshold=74,
            required_market_regime="MOMENTUM",
            required_data=("expiry", "oi", "volume", "quote"),
        )


class BreadthAlignmentStrategy(ThresholdStrategy):
    def __init__(self) -> None:
        super().__init__(
            strategy_id="breadth_alignment",
            setup_family="BREADTH_ALIGNMENT",
            display_name="Breadth / Index Alignment",
            trigger_feature="breadth_alignment_score",
            direction="BULLISH",
            trigger_threshold=67,
            required_market_regime="BREADTH_ALIGNED",
            required_data=("advance_decline", "index_ltp", "quote"),
        )

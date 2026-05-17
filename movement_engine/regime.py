from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from movement_engine.context import StrategyContext


class MovementRegime(StrEnum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    CHOP = "CHOP"
    COMPRESSION = "COMPRESSION"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    TRAP_RISK = "TRAP_RISK"
    EXHAUSTION_RISK = "EXHAUSTION_RISK"
    INCONCLUSIVE = "INCONCLUSIVE"


REGIME_SCORE_KEYS = tuple(regime.value for regime in MovementRegime)


@dataclass(frozen=True)
class MovementRegimeResult:
    primary_regime: MovementRegime
    scores: dict[str, float]
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_regime": self.primary_regime.value,
            "scores": dict(self.scores),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "is_order_action": self.is_order_action,
        }


def classify_movement_regime(context: StrategyContext | None) -> MovementRegimeResult:
    if context is None:
        return _inconclusive(["CONTEXT_REQUIRED"])

    warnings: list[str] = []
    evidence = context.to_dict()
    if context.spot_ltp is None:
        warnings.append("SPOT_LTP_MISSING")
    if context.vwap is None:
        warnings.append("VWAP_MISSING")
    if context.day_high is None or context.day_low is None:
        warnings.append("DAY_RANGE_MISSING")

    if context.spot_ltp is None or context.vwap is None:
        return _inconclusive(warnings, evidence=evidence)

    scores = _empty_scores()
    spot = context.spot_ltp
    vwap = context.vwap
    atr = _positive(context.atr)
    atr_short = _positive(context.atr_short)
    atr_long = _positive(context.atr_long)
    range_width_pct = _positive(context.range_width_pct)
    volume_z = _float(context.volume_z, 0.0)
    above_vwap_pct = _safe_pct(spot - vwap, vwap)

    range_position = _range_position(spot, context.day_low, context.day_high)
    vwap_distance = abs(above_vwap_pct)
    premium_bias = _premium_bias(context)

    if above_vwap_pct > 0:
        scores[MovementRegime.TREND_UP.value] += min(0.55, above_vwap_pct * 8.0)
    elif above_vwap_pct < 0:
        scores[MovementRegime.TREND_DOWN.value] += min(0.55, abs(above_vwap_pct) * 8.0)

    if range_position is not None:
        if range_position >= 0.70:
            scores[MovementRegime.TREND_UP.value] += 0.25
        elif range_position <= 0.30:
            scores[MovementRegime.TREND_DOWN.value] += 0.25
        elif 0.35 <= range_position <= 0.65:
            scores[MovementRegime.RANGE.value] += 0.35

    if premium_bias > 0:
        scores[MovementRegime.TREND_UP.value] += min(0.20, premium_bias)
    elif premium_bias < 0:
        scores[MovementRegime.TREND_DOWN.value] += min(0.20, abs(premium_bias))

    if vwap_distance <= 0.0015:
        scores[MovementRegime.RANGE.value] += 0.25
    if range_width_pct is not None and range_width_pct <= 0.45:
        scores[MovementRegime.COMPRESSION.value] += 0.45
        scores[MovementRegime.RANGE.value] += 0.10
    if atr_short is not None and atr_long is not None:
        atr_ratio = atr_short / atr_long if atr_long else 0.0
        evidence["atr_ratio"] = atr_ratio
        if atr_ratio <= 0.75:
            scores[MovementRegime.COMPRESSION.value] += 0.35
        elif atr_ratio >= 1.35:
            scores[MovementRegime.VOLATILITY_EXPANSION.value] += 0.45
    if atr is not None and range_width_pct is not None and atr > 0 and range_width_pct > 0.9:
        scores[MovementRegime.VOLATILITY_EXPANSION.value] += 0.20

    if volume_z >= 1.5:
        scores[MovementRegime.VOLATILITY_EXPANSION.value] += 0.20
    if volume_z <= -0.5 and scores[MovementRegime.RANGE.value] > 0:
        scores[MovementRegime.CHOP.value] += 0.15

    if _is_choppy(context):
        scores[MovementRegime.CHOP.value] += 0.80
        scores[MovementRegime.RANGE.value] += 0.05
        evidence["chop_signature"] = True

    if _has_trap_risk(context, range_position, vwap_distance):
        scores[MovementRegime.TRAP_RISK.value] += 0.55

    if _has_exhaustion_risk(context, vwap_distance, premium_bias):
        scores[MovementRegime.EXHAUSTION_RISK.value] += 0.60

    if context.volatility_state:
        state = context.volatility_state.upper()
        if state == MovementRegime.CHOP.value:
            scores[MovementRegime.CHOP.value] += 0.25
        elif state == MovementRegime.COMPRESSION.value:
            scores[MovementRegime.COMPRESSION.value] += 0.25
        elif state == MovementRegime.VOLATILITY_EXPANSION.value:
            scores[MovementRegime.VOLATILITY_EXPANSION.value] += 0.25

    if context.regime_hint:
        hint = context.regime_hint.upper()
        if hint in scores:
            scores[hint] += 0.15

    scores = {key: round(min(1.0, max(0.0, value)), 4) for key, value in scores.items()}
    primary = _primary_regime(scores)
    if scores[primary.value] <= 0.0:
        primary = MovementRegime.INCONCLUSIVE
        scores[MovementRegime.INCONCLUSIVE.value] = 1.0
        warnings.append("INSUFFICIENT_REGIME_EVIDENCE")

    return MovementRegimeResult(
        primary_regime=primary,
        scores=scores,
        warnings=_dedupe(warnings),
        evidence=evidence,
    )


def _inconclusive(warnings: list[str], evidence: dict[str, Any] | None = None) -> MovementRegimeResult:
    scores = _empty_scores()
    scores[MovementRegime.INCONCLUSIVE.value] = 1.0
    return MovementRegimeResult(
        primary_regime=MovementRegime.INCONCLUSIVE,
        scores=scores,
        warnings=_dedupe(warnings + ["INSUFFICIENT_REGIME_EVIDENCE"]),
        evidence=dict(evidence or {}),
    )


def _empty_scores() -> dict[str, float]:
    return {key: 0.0 for key in REGIME_SCORE_KEYS}


def _primary_regime(scores: dict[str, float]) -> MovementRegime:
    non_inconclusive = {key: value for key, value in scores.items() if key != MovementRegime.INCONCLUSIVE.value}
    key = max(non_inconclusive, key=lambda item: non_inconclusive[item])
    return MovementRegime(key)


def _safe_pct(delta: float, base: float | None) -> float:
    if base in (None, 0):
        return 0.0
    return delta / base


def _range_position(spot: float, low: float | None, high: float | None) -> float | None:
    if low is None or high is None or high <= low:
        return None
    return max(0.0, min(1.0, (spot - low) / (high - low)))


def _premium_bias(context: StrategyContext) -> float:
    ce = _float(context.ce_premium_change, 0.0)
    pe = _float(context.pe_premium_change, 0.0)
    return max(-1.0, min(1.0, (ce - pe) / 100.0))


def _is_choppy(context: StrategyContext) -> bool:
    near_vwap = context.spot_ltp is not None and context.vwap is not None and abs(_safe_pct(context.spot_ltp - context.vwap, context.vwap)) <= 0.001
    narrow = context.range_width_pct is not None and context.range_width_pct <= 0.35
    weak_premium = abs(_float(context.ce_premium_change, 0.0)) <= 3.0 and abs(_float(context.pe_premium_change, 0.0)) <= 3.0
    return bool(near_vwap and narrow and weak_premium)


def _has_trap_risk(context: StrategyContext, range_position: float | None, vwap_distance: float) -> bool:
    if range_position is None:
        return False
    if vwap_distance >= 0.025:
        return False
    ce = _float(context.ce_premium_change, 0.0)
    pe = _float(context.pe_premium_change, 0.0)
    upper_fail = range_position >= 0.90 and ce <= 0 and pe > 0
    lower_fail = range_position <= 0.10 and pe <= 0 and ce > 0
    return upper_fail or lower_fail


def _has_exhaustion_risk(context: StrategyContext, vwap_distance: float, premium_bias: float) -> bool:
    if vwap_distance < 0.01:
        return False
    if context.spot_ltp is None or context.vwap is None:
        return False
    stretched_up = context.spot_ltp > context.vwap and premium_bias <= 0
    stretched_down = context.spot_ltp < context.vwap and premium_bias >= 0
    return stretched_up or stretched_down


def _positive(value: float | None) -> float | None:
    parsed = _float(value, None)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _float(value: Any, default: float | None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out

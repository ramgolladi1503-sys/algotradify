from __future__ import annotations

from typing import Any

from movement_engine.candidate_pool import build_candidate_pool
from movement_engine.context import StrategyContext
from movement_engine.contract import (
    MOVEMENT_CANDIDATE_SCHEMA_VERSION,
    CandidateStatus,
    Direction,
    StrategyCandidate,
)
from movement_engine.registry import MovementStrategyRegistry


COMPRESSION_BREAKOUT_PROVIDER_ID = "COMPRESSION_BREAKOUT"
TREND_PULLBACK_PROVIDER_ID = "TREND_PULLBACK"


def register_compression_trend_providers(registry: MovementStrategyRegistry) -> MovementStrategyRegistry:
    """Register PR 62 movement providers without touching execution state."""

    registry.register_provider(COMPRESSION_BREAKOUT_PROVIDER_ID, compression_breakout_provider)
    registry.register_provider(TREND_PULLBACK_PROVIDER_ID, trend_pullback_provider)
    return registry


def compression_breakout_provider(context: StrategyContext) -> list[StrategyCandidate]:
    """Detect a basic compression-breakout candidate.

    This provider emits one raw candidate proposal. It intentionally does not
    rank, build order intent, or infer executable status.
    """

    blockers, warnings = _shared_blockers(context)
    direction = _compression_breakout_direction(context)
    if direction is None:
        blockers.append("COMPRESSION_BREAKOUT_NOT_TRIGGERED")
        direction = _direction_from_bias(context) or Direction.NO_TRADE

    blockers.extend(_directional_hard_blockers(context, direction))

    evidence = _base_evidence(context)
    evidence.update(
        {
            "provider": COMPRESSION_BREAKOUT_PROVIDER_ID,
            "strategy_family": "compression_expansion",
            "breakout_direction": direction.value,
            "atr_ratio": _atr_ratio(context),
            "range_width_pct": context.range_width_pct,
            "volume_z": context.volume_z,
            "above_day_high_pct": _pct_above(context.spot_ltp, context.day_high),
            "below_day_low_pct": _pct_below(context.spot_ltp, context.day_low),
        }
    )

    raw_score = _compression_breakout_score(context, direction, blockers)
    return [
        _candidate(
            candidate_id=_candidate_id(context, COMPRESSION_BREAKOUT_PROVIDER_ID, direction),
            strategy_id=COMPRESSION_BREAKOUT_PROVIDER_ID,
            movement_type="COMPRESSION_BREAKOUT",
            symbol=context.symbol,
            direction=direction,
            status=CandidateStatus.RAW_CANDIDATE,
            raw_score=raw_score,
            confidence_score=_bounded(raw_score - 0.06),
            price_structure_score=_compression_price_structure_score(context, direction),
            option_confirmation_score=_option_confirmation_score(context, direction),
            liquidity_score=_liquidity_score(context, direction),
            freshness_score=_freshness_score(context),
            volatility_score=_compression_volatility_score(context),
            regime_alignment_score=_regime_alignment_score(context, direction, preferred={"COMPRESSION", "VOLATILITY_EXPANSION"}),
            entry_trigger="compression resolves beyond range boundary with volume expansion",
            invalid_if="price returns inside compression range or option confirmation fails",
            rank_reason="compression breakout candidate; not ranked and not executable in PR 62",
            blockers=tuple(_dedupe(blockers)),
            warnings=tuple(_dedupe(warnings)),
            evidence=evidence,
        )
    ]


def trend_pullback_provider(context: StrategyContext) -> list[StrategyCandidate]:
    """Detect a basic trend-pullback continuation candidate."""

    blockers, warnings = _shared_blockers(context)
    direction = _trend_pullback_direction(context)
    if direction is None:
        blockers.append("TREND_PULLBACK_NOT_TRIGGERED")
        direction = _direction_from_bias(context) or Direction.NO_TRADE

    blockers.extend(_directional_hard_blockers(context, direction))

    evidence = _base_evidence(context)
    evidence.update(
        {
            "provider": TREND_PULLBACK_PROVIDER_ID,
            "strategy_family": "trend_continuation",
            "pullback_direction": direction.value,
            "vwap_distance_pct": _distance_pct(context.spot_ltp, context.vwap),
            "day_range_position": _range_position(context.spot_ltp, context.day_low, context.day_high),
            "ce_premium_change": context.ce_premium_change,
            "pe_premium_change": context.pe_premium_change,
        }
    )

    raw_score = _trend_pullback_score(context, direction, blockers)
    return [
        _candidate(
            candidate_id=_candidate_id(context, TREND_PULLBACK_PROVIDER_ID, direction),
            strategy_id=TREND_PULLBACK_PROVIDER_ID,
            movement_type="TREND_PULLBACK_CONTINUATION",
            symbol=context.symbol,
            direction=direction,
            status=CandidateStatus.RAW_CANDIDATE,
            raw_score=raw_score,
            confidence_score=_bounded(raw_score - 0.05),
            price_structure_score=_trend_pullback_price_structure_score(context, direction),
            option_confirmation_score=_option_confirmation_score(context, direction),
            liquidity_score=_liquidity_score(context, direction),
            freshness_score=_freshness_score(context),
            volatility_score=_trend_volatility_score(context),
            regime_alignment_score=_regime_alignment_score(context, direction, preferred={"TREND_UP", "TREND_DOWN"}),
            entry_trigger="trend pullback holds VWAP/structure and resumes with option confirmation",
            invalid_if="price loses VWAP/structure or opposite premium gains control",
            rank_reason="trend pullback candidate; not ranked and not executable in PR 62",
            blockers=tuple(_dedupe(blockers)),
            warnings=tuple(_dedupe(warnings)),
            evidence=evidence,
        )
    ]


def build_compression_trend_candidate_pool(context: StrategyContext):
    """Run PR 62 providers through registry and candidate pool."""

    registry = register_compression_trend_providers(MovementStrategyRegistry())
    registry_result = registry.run(context)
    return build_candidate_pool(
        registry_result.candidates,
        upstream_warnings=registry_result.warnings,
        upstream_diagnostics=registry_result.diagnostics,
    )


def _candidate(
    *,
    candidate_id: str,
    strategy_id: str,
    movement_type: str,
    symbol: str,
    direction: Direction,
    status: CandidateStatus,
    raw_score: float,
    confidence_score: float,
    price_structure_score: float,
    option_confirmation_score: float,
    liquidity_score: float,
    freshness_score: float,
    volatility_score: float,
    regime_alignment_score: float,
    entry_trigger: str,
    invalid_if: str,
    rank_reason: str,
    blockers: tuple[str, ...],
    warnings: tuple[str, ...],
    evidence: dict[str, Any],
) -> StrategyCandidate:
    if blockers and status != CandidateStatus.NO_TRADE:
        status = CandidateStatus.RAW_CANDIDATE

    return StrategyCandidate(
        schema_version=MOVEMENT_CANDIDATE_SCHEMA_VERSION,
        candidate_id=candidate_id,
        strategy_id=strategy_id,
        movement_type=movement_type,
        symbol=symbol,
        direction=direction,
        status=status,
        raw_score=_bounded(raw_score),
        confidence_score=_bounded(confidence_score),
        price_structure_score=_bounded(price_structure_score),
        option_confirmation_score=_bounded(option_confirmation_score),
        liquidity_score=_bounded(liquidity_score),
        freshness_score=_bounded(freshness_score),
        volatility_score=_bounded(volatility_score),
        regime_alignment_score=_bounded(regime_alignment_score),
        entry_trigger=entry_trigger,
        invalid_if=invalid_if,
        rank_reason=rank_reason,
        blockers=blockers,
        warnings=warnings,
        evidence=evidence,
    )


def _shared_blockers(context: StrategyContext) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if context is None:
        return ["CONTEXT_REQUIRED"], []

    if _blank(context.symbol):
        blockers.append("SYMBOL_REQUIRED")
    if context.spot_ltp is None:
        blockers.append("SPOT_LTP_MISSING")
    if context.vwap is None:
        blockers.append("VWAP_MISSING")
    if context.day_high is None or context.day_low is None:
        blockers.append("DAY_RANGE_MISSING")
    elif context.day_high <= context.day_low:
        blockers.append("INVALID_DAY_RANGE")

    if context.option_ltp_age_sec is None or context.option_ltp_age_sec > 5.0:
        blockers.append("STALE_OPTION_LTP")
    if context.quote_source and context.quote_source.upper() == "FALLBACK":
        blockers.append("FALLBACK_QUOTE_ONLY")
    if context.time_of_day and context.time_of_day.upper() == "CLOSED":
        blockers.append("MARKET_CLOSED")
    if context.regime_hint and context.regime_hint.upper() == "CHOP":
        blockers.append("NO_TRADE_CHOP")
    if context.regime_hint and context.regime_hint.upper() in {"TRAP_RISK", "EXHAUSTION_RISK"}:
        blockers.append("CONFLICTING_TRAP_SIGNAL")

    return blockers, warnings


def _directional_hard_blockers(context: StrategyContext, direction: Direction) -> list[str]:
    if direction == Direction.NO_TRADE:
        return []

    blockers: list[str] = []
    spread = context.ce_spread_pct if direction == Direction.BUY_CALL else context.pe_spread_pct
    depth = context.ce_depth if direction == Direction.BUY_CALL else context.pe_depth
    option_ltp = context.option_ce_ltp if direction == Direction.BUY_CALL else context.option_pe_ltp

    if option_ltp is None:
        blockers.append("UNRESOLVED_CONTRACT")
    if spread is None or spread > 3.0:
        blockers.append("WIDE_SPREAD")
    if depth is None or depth <= 0:
        blockers.append("MISSING_DEPTH")

    return blockers


def _compression_breakout_direction(context: StrategyContext) -> Direction | None:
    if context.spot_ltp is None or context.day_high is None or context.day_low is None:
        return None
    if not _is_compressed(context):
        return None
    if _float(context.volume_z, 0.0) < 1.0:
        return None
    if context.spot_ltp > context.day_high:
        return Direction.BUY_CALL
    if context.spot_ltp < context.day_low:
        return Direction.BUY_PUT
    return None


def _trend_pullback_direction(context: StrategyContext) -> Direction | None:
    if context.spot_ltp is None or context.vwap is None:
        return None
    position = _range_position(context.spot_ltp, context.day_low, context.day_high)
    hint = (context.regime_hint or "").upper()
    ce_bias = _float(context.ce_premium_change, 0.0) - _float(context.pe_premium_change, 0.0)
    pe_bias = -ce_bias
    near_vwap = abs(_distance_pct(context.spot_ltp, context.vwap)) <= 0.006

    if hint == "TREND_UP" and near_vwap and context.spot_ltp >= context.vwap and ce_bias >= 5.0:
        return Direction.BUY_CALL
    if hint == "TREND_DOWN" and near_vwap and context.spot_ltp <= context.vwap and pe_bias >= 5.0:
        return Direction.BUY_PUT

    if position is not None and 0.45 <= position <= 0.75 and context.spot_ltp >= context.vwap and ce_bias >= 10.0:
        return Direction.BUY_CALL
    if position is not None and 0.25 <= position <= 0.55 and context.spot_ltp <= context.vwap and pe_bias >= 10.0:
        return Direction.BUY_PUT

    return None


def _is_compressed(context: StrategyContext) -> bool:
    atr_ratio = _atr_ratio(context)
    narrow_range = context.range_width_pct is not None and context.range_width_pct <= 0.45
    atr_compression = atr_ratio is not None and atr_ratio <= 0.85
    state_compression = bool(context.volatility_state and context.volatility_state.upper() == "COMPRESSION")
    hint_compression = bool(context.regime_hint and context.regime_hint.upper() == "COMPRESSION")
    return narrow_range or atr_compression or state_compression or hint_compression


def _direction_from_bias(context: StrategyContext) -> Direction | None:
    ce = _float(context.ce_premium_change, 0.0)
    pe = _float(context.pe_premium_change, 0.0)
    if ce > pe:
        return Direction.BUY_CALL
    if pe > ce:
        return Direction.BUY_PUT
    return None


def _compression_breakout_score(context: StrategyContext, direction: Direction, blockers: list[str]) -> float:
    if blockers or direction == Direction.NO_TRADE:
        return 0.0
    score = 0.30
    score += _compression_price_structure_score(context, direction) * 0.25
    score += _compression_volatility_score(context) * 0.20
    score += _option_confirmation_score(context, direction) * 0.15
    score += _freshness_score(context) * 0.10
    return _bounded(score)


def _trend_pullback_score(context: StrategyContext, direction: Direction, blockers: list[str]) -> float:
    if blockers or direction == Direction.NO_TRADE:
        return 0.0
    score = 0.30
    score += _trend_pullback_price_structure_score(context, direction) * 0.25
    score += _regime_alignment_score(context, direction, preferred={"TREND_UP", "TREND_DOWN"}) * 0.20
    score += _option_confirmation_score(context, direction) * 0.15
    score += _freshness_score(context) * 0.10
    return _bounded(score)


def _compression_price_structure_score(context: StrategyContext, direction: Direction) -> float:
    if context.spot_ltp is None or context.day_high is None or context.day_low is None:
        return 0.0
    if direction == Direction.BUY_CALL:
        return _bounded(0.40 + min(0.50, _pct_above(context.spot_ltp, context.day_high) * 100.0))
    if direction == Direction.BUY_PUT:
        return _bounded(0.40 + min(0.50, _pct_below(context.spot_ltp, context.day_low) * 100.0))
    return 0.0


def _trend_pullback_price_structure_score(context: StrategyContext, direction: Direction) -> float:
    if context.spot_ltp is None or context.vwap in (None, 0):
        return 0.0
    distance = abs(_distance_pct(context.spot_ltp, context.vwap))
    score = 0.85 - min(0.55, distance * 70.0)
    if direction == Direction.BUY_CALL and context.spot_ltp >= context.vwap:
        score += 0.05
    if direction == Direction.BUY_PUT and context.spot_ltp <= context.vwap:
        score += 0.05
    return _bounded(score)


def _option_confirmation_score(context: StrategyContext, direction: Direction) -> float:
    if direction == Direction.BUY_CALL:
        confirmation = _float(context.ce_premium_change, 0.0) - _float(context.pe_premium_change, 0.0)
    elif direction == Direction.BUY_PUT:
        confirmation = _float(context.pe_premium_change, 0.0) - _float(context.ce_premium_change, 0.0)
    else:
        return 0.0
    return _bounded(0.35 + max(0.0, min(0.55, confirmation / 60.0)))


def _liquidity_score(context: StrategyContext, direction: Direction) -> float:
    spread = context.ce_spread_pct if direction == Direction.BUY_CALL else context.pe_spread_pct
    depth = context.ce_depth if direction == Direction.BUY_CALL else context.pe_depth
    if spread is None or depth is None:
        return 0.0
    score = 1.0
    if spread > 1.5:
        score -= 0.45
    if spread > 3.0:
        score -= 0.30
    if depth < 100:
        score -= 0.45
    return _bounded(score)


def _freshness_score(context: StrategyContext) -> float:
    if context.option_ltp_age_sec is None:
        return 0.0
    return _bounded(1.0 - (max(0.0, context.option_ltp_age_sec) / 10.0))


def _compression_volatility_score(context: StrategyContext) -> float:
    score = 0.35
    atr_ratio = _atr_ratio(context)
    if atr_ratio is not None and atr_ratio <= 0.85:
        score += 0.25
    if context.range_width_pct is not None and context.range_width_pct <= 0.45:
        score += 0.20
    if context.volatility_state and context.volatility_state.upper() == "COMPRESSION":
        score += 0.15
    if _float(context.volume_z, 0.0) >= 1.0:
        score += 0.10
    return _bounded(score)


def _trend_volatility_score(context: StrategyContext) -> float:
    if context.volatility_state and context.volatility_state.upper() in {"TREND_UP", "TREND_DOWN", "VOLATILITY_EXPANSION"}:
        return 0.70
    atr_ratio = _atr_ratio(context)
    if atr_ratio is not None:
        return _bounded(0.45 + min(0.30, atr_ratio / 5.0))
    return 0.50


def _regime_alignment_score(context: StrategyContext, direction: Direction, *, preferred: set[str]) -> float:
    hint = (context.regime_hint or "").upper()
    if direction == Direction.BUY_CALL and hint == "TREND_UP":
        return 0.85
    if direction == Direction.BUY_PUT and hint == "TREND_DOWN":
        return 0.85
    if hint in preferred:
        return 0.75
    if hint in {"VOLATILITY_EXPANSION", "COMPRESSION"}:
        return 0.65
    if hint in {"CHOP", "TRAP_RISK", "EXHAUSTION_RISK"}:
        return 0.15
    return 0.45


def _base_evidence(context: StrategyContext) -> dict[str, Any]:
    return {
        "symbol": context.symbol,
        "ts_epoch": context.ts_epoch,
        "spot_ltp": context.spot_ltp,
        "vwap": context.vwap,
        "day_high": context.day_high,
        "day_low": context.day_low,
        "range_width_pct": context.range_width_pct,
        "atr_short": context.atr_short,
        "atr_long": context.atr_long,
        "regime_hint": context.regime_hint,
        "volatility_state": context.volatility_state,
        "option_ltp_age_sec": context.option_ltp_age_sec,
        "quote_source": context.quote_source,
        "ce_spread_pct": context.ce_spread_pct,
        "pe_spread_pct": context.pe_spread_pct,
        "ce_depth": context.ce_depth,
        "pe_depth": context.pe_depth,
        "is_order_action": False,
    }


def _candidate_id(context: StrategyContext, provider_id: str, direction: Direction) -> str:
    return f"{provider_id.lower()}:{context.symbol}:{int(context.ts_epoch)}:{direction.value.lower()}"


def _atr_ratio(context: StrategyContext) -> float | None:
    if context.atr_short is None or context.atr_long in (None, 0):
        return None
    return context.atr_short / context.atr_long


def _range_position(value: float | None, low: float | None, high: float | None) -> float | None:
    if value is None or low is None or high is None or high <= low:
        return None
    return max(0.0, min(1.0, (value - low) / (high - low)))


def _pct_above(value: float | None, reference: float | None) -> float:
    if value is None or reference in (None, 0):
        return 0.0
    return max(0.0, (value - reference) / reference)


def _pct_below(value: float | None, reference: float | None) -> float:
    if value is None or reference in (None, 0):
        return 0.0
    return max(0.0, (reference - value) / reference)


def _distance_pct(value: float | None, reference: float | None) -> float:
    if value is None or reference in (None, 0):
        return 0.0
    return (value - reference) / reference


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bounded(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out

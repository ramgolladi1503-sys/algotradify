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


VWAP_RECLAIM_PROVIDER_ID = "VWAP_RECLAIM"
FAILED_BREAKOUT_TRAP_PROVIDER_ID = "FAILED_BREAKOUT_TRAP"


def register_vwap_trap_providers(registry: MovementStrategyRegistry) -> MovementStrategyRegistry:
    """Register PR 63 movement providers without touching execution state."""

    registry.register_provider(VWAP_RECLAIM_PROVIDER_ID, vwap_reclaim_provider)
    registry.register_provider(FAILED_BREAKOUT_TRAP_PROVIDER_ID, failed_breakout_trap_provider)
    return registry


def vwap_reclaim_provider(context: StrategyContext) -> list[StrategyCandidate]:
    """Detect a basic VWAP reclaim/loss candidate.

    The provider emits one raw candidate proposal. It does not rank, execute,
    build order intent, or infer broker readiness.
    """

    blockers, warnings = _shared_blockers(context)
    direction = _vwap_reclaim_direction(context)
    if direction is None:
        blockers.append("VWAP_RECLAIM_NOT_TRIGGERED")
        direction = _direction_from_bias(context) or Direction.NO_TRADE

    blockers.extend(_directional_hard_blockers(context, direction))

    evidence = _base_evidence(context)
    evidence.update(
        {
            "provider": VWAP_RECLAIM_PROVIDER_ID,
            "strategy_family": "vwap_reclaim",
            "reclaim_direction": direction.value,
            "vwap_distance_pct": _distance_pct(context.spot_ltp, context.vwap),
            "day_range_position": _range_position(context.spot_ltp, context.day_low, context.day_high),
            "ce_premium_change": context.ce_premium_change,
            "pe_premium_change": context.pe_premium_change,
        }
    )

    raw_score = _vwap_reclaim_score(context, direction, blockers)
    return [
        _candidate(
            candidate_id=_candidate_id(context, VWAP_RECLAIM_PROVIDER_ID, direction),
            strategy_id=VWAP_RECLAIM_PROVIDER_ID,
            movement_type="VWAP_RECLAIM",
            symbol=context.symbol,
            direction=direction,
            status=CandidateStatus.RAW_CANDIDATE,
            raw_score=raw_score,
            confidence_score=_bounded(raw_score - 0.05),
            price_structure_score=_vwap_price_structure_score(context, direction),
            option_confirmation_score=_option_confirmation_score(context, direction),
            liquidity_score=_liquidity_score(context, direction),
            freshness_score=_freshness_score(context),
            volatility_score=_volatility_score(context),
            regime_alignment_score=_regime_alignment_score(context, direction),
            entry_trigger="price reclaims or loses VWAP with option premium confirmation",
            invalid_if="price fails back across VWAP or opposite premium gains control",
            rank_reason="VWAP reclaim candidate; not ranked and not executable in PR 63",
            blockers=tuple(_dedupe(blockers)),
            warnings=tuple(_dedupe(warnings)),
            evidence=evidence,
        )
    ]


def failed_breakout_trap_provider(context: StrategyContext) -> list[StrategyCandidate]:
    """Detect a basic failed-breakout trap candidate.

    This provider looks for upper-boundary failures that favor puts and
    lower-boundary failures that favor calls. It stays candidate-only.
    """

    blockers, warnings = _shared_blockers(context)
    direction = _failed_breakout_trap_direction(context)
    if direction is None:
        blockers.append("FAILED_BREAKOUT_TRAP_NOT_TRIGGERED")
        direction = _direction_from_bias(context) or Direction.NO_TRADE

    blockers.extend(_directional_hard_blockers(context, direction))

    evidence = _base_evidence(context)
    evidence.update(
        {
            "provider": FAILED_BREAKOUT_TRAP_PROVIDER_ID,
            "strategy_family": "failed_breakout_trap",
            "trap_direction": direction.value,
            "day_range_position": _range_position(context.spot_ltp, context.day_low, context.day_high),
            "upper_boundary_distance_pct": _nearest_upper_boundary_distance_pct(context),
            "lower_boundary_distance_pct": _nearest_lower_boundary_distance_pct(context),
            "ce_premium_change": context.ce_premium_change,
            "pe_premium_change": context.pe_premium_change,
        }
    )

    raw_score = _failed_breakout_trap_score(context, direction, blockers)
    return [
        _candidate(
            candidate_id=_candidate_id(context, FAILED_BREAKOUT_TRAP_PROVIDER_ID, direction),
            strategy_id=FAILED_BREAKOUT_TRAP_PROVIDER_ID,
            movement_type="FAILED_BREAKOUT_TRAP",
            symbol=context.symbol,
            direction=direction,
            status=CandidateStatus.RAW_CANDIDATE,
            raw_score=raw_score,
            confidence_score=_bounded(raw_score - 0.06),
            price_structure_score=_trap_price_structure_score(context, direction),
            option_confirmation_score=_option_confirmation_score(context, direction),
            liquidity_score=_liquidity_score(context, direction),
            freshness_score=_freshness_score(context),
            volatility_score=_volatility_score(context),
            regime_alignment_score=_trap_regime_alignment_score(context, direction),
            entry_trigger="failed breakout at range boundary with opposite option premium confirmation",
            invalid_if="price accepts beyond failed breakout boundary or trap premium confirmation reverses",
            rank_reason="failed breakout trap candidate; not ranked and not executable in PR 63",
            blockers=tuple(_dedupe(blockers)),
            warnings=tuple(_dedupe(warnings)),
            evidence=evidence,
        )
    ]


def build_vwap_trap_candidate_pool(context: StrategyContext):
    """Run PR 63 providers through registry and candidate pool."""

    registry = register_vwap_trap_providers(MovementStrategyRegistry())
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
        warnings.append("DAY_RANGE_MISSING")
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


def _vwap_reclaim_direction(context: StrategyContext) -> Direction | None:
    if context.spot_ltp is None or context.vwap is None:
        return None
    distance = _distance_pct(context.spot_ltp, context.vwap)
    near_vwap = abs(distance) <= 0.006
    ce_bias = _float(context.ce_premium_change, 0.0) - _float(context.pe_premium_change, 0.0)
    pe_bias = -ce_bias

    if near_vwap and context.spot_ltp >= context.vwap and ce_bias >= 6.0:
        return Direction.BUY_CALL
    if near_vwap and context.spot_ltp <= context.vwap and pe_bias >= 6.0:
        return Direction.BUY_PUT
    return None


def _failed_breakout_trap_direction(context: StrategyContext) -> Direction | None:
    if context.spot_ltp is None:
        return None

    position = _range_position(context.spot_ltp, context.day_low, context.day_high)
    upper_fail = _near_upper_boundary(context) and _float(context.ce_premium_change, 0.0) <= 1.0 and _float(context.pe_premium_change, 0.0) >= 6.0
    lower_fail = _near_lower_boundary(context) and _float(context.pe_premium_change, 0.0) <= 1.0 and _float(context.ce_premium_change, 0.0) >= 6.0

    if upper_fail or (position is not None and position >= 0.85 and _float(context.pe_premium_change, 0.0) - _float(context.ce_premium_change, 0.0) >= 8.0):
        return Direction.BUY_PUT
    if lower_fail or (position is not None and position <= 0.15 and _float(context.ce_premium_change, 0.0) - _float(context.pe_premium_change, 0.0) >= 8.0):
        return Direction.BUY_CALL
    return None


def _direction_from_bias(context: StrategyContext) -> Direction | None:
    ce = _float(context.ce_premium_change, 0.0)
    pe = _float(context.pe_premium_change, 0.0)
    if ce > pe:
        return Direction.BUY_CALL
    if pe > ce:
        return Direction.BUY_PUT
    return None


def _vwap_reclaim_score(context: StrategyContext, direction: Direction, blockers: list[str]) -> float:
    if blockers or direction == Direction.NO_TRADE:
        return 0.0
    score = 0.30
    score += _vwap_price_structure_score(context, direction) * 0.30
    score += _option_confirmation_score(context, direction) * 0.20
    score += _freshness_score(context) * 0.10
    score += _regime_alignment_score(context, direction) * 0.10
    return _bounded(score)


def _failed_breakout_trap_score(context: StrategyContext, direction: Direction, blockers: list[str]) -> float:
    if blockers or direction == Direction.NO_TRADE:
        return 0.0
    score = 0.30
    score += _trap_price_structure_score(context, direction) * 0.30
    score += _option_confirmation_score(context, direction) * 0.20
    score += _trap_regime_alignment_score(context, direction) * 0.10
    score += _freshness_score(context) * 0.10
    return _bounded(score)


def _vwap_price_structure_score(context: StrategyContext, direction: Direction) -> float:
    if context.spot_ltp is None or context.vwap in (None, 0):
        return 0.0
    distance = abs(_distance_pct(context.spot_ltp, context.vwap))
    score = 0.85 - min(0.55, distance * 80.0)
    if direction == Direction.BUY_CALL and context.spot_ltp >= context.vwap:
        score += 0.05
    if direction == Direction.BUY_PUT and context.spot_ltp <= context.vwap:
        score += 0.05
    return _bounded(score)


def _trap_price_structure_score(context: StrategyContext, direction: Direction) -> float:
    position = _range_position(context.spot_ltp, context.day_low, context.day_high)
    if position is None:
        return 0.45
    if direction == Direction.BUY_PUT:
        return _bounded(0.45 + max(0.0, position - 0.70))
    if direction == Direction.BUY_CALL:
        return _bounded(0.45 + max(0.0, 0.30 - position))
    return 0.0


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


def _volatility_score(context: StrategyContext) -> float:
    if context.volatility_state and context.volatility_state.upper() in {"VOLATILITY_EXPANSION", "TREND_UP", "TREND_DOWN", "TRAP_RISK"}:
        return 0.70
    if context.atr_short is not None and context.atr_long not in (None, 0):
        return _bounded((context.atr_short / context.atr_long) / 1.5)
    return 0.50


def _regime_alignment_score(context: StrategyContext, direction: Direction) -> float:
    hint = (context.regime_hint or "").upper()
    if direction == Direction.BUY_CALL and hint == "TREND_UP":
        return 0.80
    if direction == Direction.BUY_PUT and hint == "TREND_DOWN":
        return 0.80
    if hint in {"RANGE", "VOLATILITY_EXPANSION"}:
        return 0.60
    if hint in {"CHOP", "EXHAUSTION_RISK"}:
        return 0.15
    return 0.45


def _trap_regime_alignment_score(context: StrategyContext, direction: Direction) -> float:
    hint = (context.regime_hint or "").upper()
    if hint == "TRAP_RISK":
        return 0.90
    if hint in {"RANGE", "EXHAUSTION_RISK"}:
        return 0.65
    if hint in {"CHOP"}:
        return 0.15
    return _regime_alignment_score(context, direction)


def _base_evidence(context: StrategyContext) -> dict[str, Any]:
    return {
        "symbol": context.symbol,
        "ts_epoch": context.ts_epoch,
        "spot_ltp": context.spot_ltp,
        "vwap": context.vwap,
        "day_high": context.day_high,
        "day_low": context.day_low,
        "orb_high": context.orb_high,
        "orb_low": context.orb_low,
        "prev_day_high": context.prev_day_high,
        "prev_day_low": context.prev_day_low,
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


def _near_upper_boundary(context: StrategyContext) -> bool:
    if context.spot_ltp is None:
        return False
    boundaries = [context.day_high, context.orb_high, context.prev_day_high]
    return any(_near(context.spot_ltp, boundary, tolerance=0.004) for boundary in boundaries if boundary is not None)


def _near_lower_boundary(context: StrategyContext) -> bool:
    if context.spot_ltp is None:
        return False
    boundaries = [context.day_low, context.orb_low, context.prev_day_low]
    return any(_near(context.spot_ltp, boundary, tolerance=0.004) for boundary in boundaries if boundary is not None)


def _nearest_upper_boundary_distance_pct(context: StrategyContext) -> float | None:
    if context.spot_ltp is None:
        return None
    distances = [_distance_pct(context.spot_ltp, boundary) for boundary in (context.day_high, context.orb_high, context.prev_day_high) if boundary not in (None, 0)]
    return min(distances, key=abs) if distances else None


def _nearest_lower_boundary_distance_pct(context: StrategyContext) -> float | None:
    if context.spot_ltp is None:
        return None
    distances = [_distance_pct(context.spot_ltp, boundary) for boundary in (context.day_low, context.orb_low, context.prev_day_low) if boundary not in (None, 0)]
    return min(distances, key=abs) if distances else None


def _near(value: float, reference: float | None, *, tolerance: float) -> bool:
    if reference in (None, 0):
        return False
    return abs(_distance_pct(value, reference)) <= tolerance


def _range_position(value: float | None, low: float | None, high: float | None) -> float | None:
    if value is None or low is None or high is None or high <= low:
        return None
    return max(0.0, min(1.0, (value - low) / (high - low)))


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

from __future__ import annotations

from dataclasses import replace
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


OPENING_DRIVE_PROVIDER_ID = "OPENING_DRIVE"
ORB_RETEST_PROVIDER_ID = "ORB_RETEST"


def register_opening_drive_orb_providers(registry: MovementStrategyRegistry) -> MovementStrategyRegistry:
    """Register PR 61 movement providers on the supplied registry.

    This function only registers provider callables. It does not run scans,
    build order intents, call brokers, or touch execution state.
    """

    registry.register_provider(OPENING_DRIVE_PROVIDER_ID, opening_drive_provider)
    registry.register_provider(ORB_RETEST_PROVIDER_ID, orb_retest_provider)
    return registry


def opening_drive_provider(context: StrategyContext) -> list[StrategyCandidate]:
    """Detect a basic opening-drive candidate from context evidence.

    The provider emits at most one raw candidate. Missing or unsafe evidence is
    expressed as blockers/warnings on the candidate; pool-level hard blockers
    decide whether the candidate remains raw or becomes blocked.
    """

    blockers, warnings = _shared_blockers(context)
    warnings.extend(_opening_window_warnings(context))

    direction = _breakout_direction(context)
    if direction is None:
        blockers.append("OPENING_DRIVE_NOT_TRIGGERED")
        direction = _direction_from_bias(context) or Direction.NO_TRADE

    evidence = _base_evidence(context)
    evidence.update(
        {
            "provider": OPENING_DRIVE_PROVIDER_ID,
            "strategy_family": "opening_momentum",
            "breakout_direction": direction.value,
            "above_orb_high_pct": _pct_above(context.spot_ltp, context.orb_high),
            "below_orb_low_pct": _pct_below(context.spot_ltp, context.orb_low),
            "volume_z": context.volume_z,
            "minutes_since_open": context.minutes_since_open,
        }
    )

    raw_score = _opening_drive_score(context, direction, blockers)
    candidate = _candidate(
        candidate_id=_candidate_id(context, OPENING_DRIVE_PROVIDER_ID, direction),
        strategy_id=OPENING_DRIVE_PROVIDER_ID,
        movement_type="OPENING_MOMENTUM_EXPANSION",
        symbol=context.symbol,
        direction=direction,
        status=CandidateStatus.RAW_CANDIDATE,
        raw_score=raw_score,
        confidence_score=_bounded(raw_score - 0.05),
        price_structure_score=_opening_price_structure_score(context, direction),
        option_confirmation_score=_option_confirmation_score(context, direction),
        liquidity_score=_liquidity_score(context, direction),
        freshness_score=_freshness_score(context),
        volatility_score=_volatility_score(context),
        regime_alignment_score=_regime_alignment_score(context, direction),
        entry_trigger="opening range break with early volume expansion",
        invalid_if="price returns inside opening range or option confirmation disappears",
        rank_reason="opening drive candidate; not ranked and not executable in PR 61",
        blockers=tuple(_dedupe(blockers)),
        warnings=tuple(_dedupe(warnings)),
        evidence=evidence,
    )
    return [candidate]


def orb_retest_provider(context: StrategyContext) -> list[StrategyCandidate]:
    """Detect a basic opening-range breakout retest candidate.

    The provider emits at most one raw candidate. It deliberately does not rank,
    execute, or infer broker-ready status.
    """

    blockers, warnings = _shared_blockers(context)
    direction = _orb_retest_direction(context)
    if direction is None:
        blockers.append("ORB_RETEST_NOT_TRIGGERED")
        direction = _direction_from_bias(context) or Direction.NO_TRADE

    evidence = _base_evidence(context)
    evidence.update(
        {
            "provider": ORB_RETEST_PROVIDER_ID,
            "strategy_family": "opening_range_retest",
            "retest_direction": direction.value,
            "orb_high_distance_pct": _distance_pct(context.spot_ltp, context.orb_high),
            "orb_low_distance_pct": _distance_pct(context.spot_ltp, context.orb_low),
            "minutes_since_open": context.minutes_since_open,
        }
    )

    raw_score = _orb_retest_score(context, direction, blockers)
    candidate = _candidate(
        candidate_id=_candidate_id(context, ORB_RETEST_PROVIDER_ID, direction),
        strategy_id=ORB_RETEST_PROVIDER_ID,
        movement_type="ORB_BREAKOUT_RETEST",
        symbol=context.symbol,
        direction=direction,
        status=CandidateStatus.RAW_CANDIDATE,
        raw_score=raw_score,
        confidence_score=_bounded(raw_score - 0.07),
        price_structure_score=_orb_price_structure_score(context, direction),
        option_confirmation_score=_option_confirmation_score(context, direction),
        liquidity_score=_liquidity_score(context, direction),
        freshness_score=_freshness_score(context),
        volatility_score=_volatility_score(context),
        regime_alignment_score=_regime_alignment_score(context, direction),
        entry_trigger="opening range breakout retest holding the broken range boundary",
        invalid_if="price closes back through the retest boundary or premium confirmation reverses",
        rank_reason="ORB retest candidate; not ranked and not executable in PR 61",
        blockers=tuple(_dedupe(blockers)),
        warnings=tuple(_dedupe(warnings)),
        evidence=evidence,
    )
    return [candidate]


def build_opening_drive_orb_candidate_pool(context: StrategyContext):
    """Run PR 61 providers through registry and candidate pool.

    This helper proves the intended integration path while staying read-only.
    """

    registry = register_opening_drive_orb_providers(MovementStrategyRegistry())
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
        # Keep provider output as a candidate proposal. The candidate pool owns
        # hard-block conversion to BLOCKED_CANDIDATE.
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
        warnings.append("VWAP_MISSING")
    if context.orb_high is None or context.orb_low is None:
        blockers.append("OPENING_RANGE_MISSING")
    elif context.orb_high <= context.orb_low:
        blockers.append("INVALID_OPENING_RANGE")

    if context.option_ltp_age_sec is None:
        blockers.append("STALE_OPTION_LTP")
    elif context.option_ltp_age_sec > 5.0:
        blockers.append("STALE_OPTION_LTP")

    if context.quote_source and context.quote_source.upper() == "FALLBACK":
        blockers.append("FALLBACK_QUOTE_ONLY")

    if context.time_of_day and context.time_of_day.upper() == "CLOSED":
        blockers.append("MARKET_CLOSED")

    return blockers, warnings


def _opening_window_warnings(context: StrategyContext) -> list[str]:
    if context.minutes_since_open is None:
        return ["OPENING_MINUTE_MISSING"]
    if context.minutes_since_open > 45:
        return ["OPENING_DRIVE_LATE_WINDOW"]
    return []


def _breakout_direction(context: StrategyContext) -> Direction | None:
    if context.spot_ltp is None or context.orb_high is None or context.orb_low is None:
        return None
    if context.spot_ltp > context.orb_high and _float(context.volume_z, 0.0) >= 0.8:
        return Direction.BUY_CALL
    if context.spot_ltp < context.orb_low and _float(context.volume_z, 0.0) >= 0.8:
        return Direction.BUY_PUT
    return None


def _orb_retest_direction(context: StrategyContext) -> Direction | None:
    if context.spot_ltp is None or context.orb_high is None or context.orb_low is None:
        return None
    if context.vwap is None:
        return None

    tolerance = max(0.0015, _safe_pct(_float(context.atr, 0.0), context.spot_ltp) * 0.15)
    near_high = abs(_safe_pct(context.spot_ltp - context.orb_high, context.orb_high)) <= tolerance
    near_low = abs(_safe_pct(context.spot_ltp - context.orb_low, context.orb_low)) <= tolerance

    if near_high and context.spot_ltp >= context.vwap and _float(context.ce_premium_change, 0.0) >= _float(context.pe_premium_change, 0.0):
        return Direction.BUY_CALL
    if near_low and context.spot_ltp <= context.vwap and _float(context.pe_premium_change, 0.0) >= _float(context.ce_premium_change, 0.0):
        return Direction.BUY_PUT
    return None


def _direction_from_bias(context: StrategyContext) -> Direction | None:
    ce = _float(context.ce_premium_change, 0.0)
    pe = _float(context.pe_premium_change, 0.0)
    if ce > pe:
        return Direction.BUY_CALL
    if pe > ce:
        return Direction.BUY_PUT
    return None


def _opening_drive_score(context: StrategyContext, direction: Direction, blockers: list[str]) -> float:
    if blockers or direction == Direction.NO_TRADE:
        return 0.0
    score = 0.35
    score += min(0.25, max(0.0, _float(context.volume_z, 0.0)) * 0.08)
    score += _option_confirmation_score(context, direction) * 0.20
    score += _regime_alignment_score(context, direction) * 0.10
    score += _freshness_score(context) * 0.10
    return _bounded(score)


def _orb_retest_score(context: StrategyContext, direction: Direction, blockers: list[str]) -> float:
    if blockers or direction == Direction.NO_TRADE:
        return 0.0
    score = 0.30
    score += _orb_price_structure_score(context, direction) * 0.25
    score += _option_confirmation_score(context, direction) * 0.20
    score += _freshness_score(context) * 0.10
    score += _regime_alignment_score(context, direction) * 0.15
    return _bounded(score)


def _opening_price_structure_score(context: StrategyContext, direction: Direction) -> float:
    if context.spot_ltp is None or context.orb_high is None or context.orb_low is None:
        return 0.0
    if direction == Direction.BUY_CALL:
        return _bounded(0.45 + min(0.45, max(0.0, _pct_above(context.spot_ltp, context.orb_high)) * 80.0))
    if direction == Direction.BUY_PUT:
        return _bounded(0.45 + min(0.45, max(0.0, _pct_below(context.spot_ltp, context.orb_low)) * 80.0))
    return 0.0


def _orb_price_structure_score(context: StrategyContext, direction: Direction) -> float:
    if context.spot_ltp is None or context.orb_high is None or context.orb_low is None:
        return 0.0
    if direction == Direction.BUY_CALL:
        distance = abs(_distance_pct(context.spot_ltp, context.orb_high))
    elif direction == Direction.BUY_PUT:
        distance = abs(_distance_pct(context.spot_ltp, context.orb_low))
    else:
        return 0.0
    return _bounded(0.85 - min(0.55, distance * 100.0))


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
    if context.volatility_state:
        state = context.volatility_state.upper()
        if state in {"VOLATILITY_EXPANSION", "TREND_UP", "TREND_DOWN"}:
            return 0.75
        if state == "COMPRESSION":
            return 0.45
        if state == "CHOP":
            return 0.15
    if context.atr_short is not None and context.atr_long not in (None, 0):
        return _bounded((context.atr_short / context.atr_long) / 1.5)
    return 0.50


def _regime_alignment_score(context: StrategyContext, direction: Direction) -> float:
    hint = (context.regime_hint or "").upper()
    if direction == Direction.BUY_CALL and hint == "TREND_UP":
        return 0.85
    if direction == Direction.BUY_PUT and hint == "TREND_DOWN":
        return 0.85
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
        "orb_high": context.orb_high,
        "orb_low": context.orb_low,
        "regime_hint": context.regime_hint,
        "option_ltp_age_sec": context.option_ltp_age_sec,
        "quote_source": context.quote_source,
        "is_order_action": False,
    }


def _candidate_id(context: StrategyContext, provider_id: str, direction: Direction) -> str:
    return f"{provider_id.lower()}:{context.symbol}:{int(context.ts_epoch)}:{direction.value.lower()}"


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


def _safe_pct(delta: float | None, base: float | None) -> float:
    if delta is None or base in (None, 0):
        return 0.0
    return delta / base


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

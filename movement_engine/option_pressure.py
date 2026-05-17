from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Iterable

from movement_engine.context import StrategyContext
from movement_engine.contract import CandidateStatus, Direction, StrategyCandidate


OPTION_PRESSURE_EVIDENCE_KEY = "option_pressure_confirmation"


class OptionPressureStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    WEAK_CONFIRMATION = "WEAK_CONFIRMATION"
    CONFLICTING_PRESSURE = "CONFLICTING_PRESSURE"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class OptionPressureConfirmationResult:
    direction: Direction
    status: OptionPressureStatus
    pressure_score: float
    ce_pressure_score: float
    pe_pressure_score: float
    premium_bias: float
    spread_quality_score: float
    depth_quality_score: float
    freshness_score: float
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence: dict[str, Any] | None = None

    @property
    def is_order_action(self) -> bool:
        return False

    @property
    def confirmed(self) -> bool:
        return self.status == OptionPressureStatus.CONFIRMED

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction.value,
            "status": self.status.value,
            "confirmed": self.confirmed,
            "pressure_score": self.pressure_score,
            "ce_pressure_score": self.ce_pressure_score,
            "pe_pressure_score": self.pe_pressure_score,
            "premium_bias": self.premium_bias,
            "spread_quality_score": self.spread_quality_score,
            "depth_quality_score": self.depth_quality_score,
            "freshness_score": self.freshness_score,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence or {}),
            "is_order_action": self.is_order_action,
        }


def confirm_option_pressure(context: StrategyContext | None, direction: Direction | str) -> OptionPressureConfirmationResult:
    parsed_direction = _parse_direction(direction)
    if context is None:
        return _result(
            direction=parsed_direction,
            status=OptionPressureStatus.BLOCKED,
            blockers=["CONTEXT_REQUIRED"],
            evidence={},
        )

    blockers, warnings = _base_blockers(context, parsed_direction)
    ce_pressure = _side_pressure_score(
        premium_change=context.ce_premium_change,
        spread_pct=context.ce_spread_pct,
        depth=context.ce_depth,
        option_ltp=context.option_ce_ltp,
    )
    pe_pressure = _side_pressure_score(
        premium_change=context.pe_premium_change,
        spread_pct=context.pe_spread_pct,
        depth=context.pe_depth,
        option_ltp=context.option_pe_ltp,
    )
    premium_bias = _premium_bias(context)
    spread_quality = _directional_spread_quality(context, parsed_direction)
    depth_quality = _directional_depth_quality(context, parsed_direction)
    freshness = _freshness_score(context)
    pressure_score = _directional_pressure_score(
        direction=parsed_direction,
        ce_pressure=ce_pressure,
        pe_pressure=pe_pressure,
        premium_bias=premium_bias,
        spread_quality=spread_quality,
        depth_quality=depth_quality,
        freshness=freshness,
    )

    if parsed_direction == Direction.NO_TRADE:
        warnings.append("OPTION_PRESSURE_NOT_APPLICABLE_FOR_NO_TRADE")
        status = OptionPressureStatus.NOT_APPLICABLE if not blockers else OptionPressureStatus.BLOCKED
    elif blockers:
        status = OptionPressureStatus.BLOCKED
    elif _has_conflicting_pressure(parsed_direction, premium_bias):
        status = OptionPressureStatus.CONFLICTING_PRESSURE
        blockers.append("CONFLICTING_OPTION_PRESSURE")
    elif pressure_score >= 0.62:
        status = OptionPressureStatus.CONFIRMED
    else:
        status = OptionPressureStatus.WEAK_CONFIRMATION
        warnings.append("WEAK_OPTION_CONFIRMATION")

    return _result(
        direction=parsed_direction,
        status=status,
        pressure_score=pressure_score,
        ce_pressure_score=ce_pressure,
        pe_pressure_score=pe_pressure,
        premium_bias=premium_bias,
        spread_quality_score=spread_quality,
        depth_quality_score=depth_quality,
        freshness_score=freshness,
        blockers=blockers,
        warnings=warnings,
        evidence=_evidence(context),
    )


def attach_option_pressure_confirmation(
    candidate: StrategyCandidate,
    context: StrategyContext | None,
) -> StrategyCandidate:
    """Attach read-only option-pressure evidence to one candidate.

    The returned candidate is still not an order action. Hard blockers are added
    to the candidate so the existing candidate pool can block unsafe candidates.
    """

    confirmation = confirm_option_pressure(context, candidate.direction)
    evidence = dict(candidate.evidence)
    evidence[OPTION_PRESSURE_EVIDENCE_KEY] = confirmation.to_dict()

    blockers = list(candidate.blockers)
    warnings = list(candidate.warnings)
    blockers.extend(confirmation.blockers)
    warnings.extend(confirmation.warnings)

    if confirmation.status == OptionPressureStatus.CONFLICTING_PRESSURE:
        blockers.append("CONFLICTING_TRAP_SIGNAL")
    if confirmation.status == OptionPressureStatus.WEAK_CONFIRMATION:
        warnings.append("WEAK_OPTION_CONFIRMATION")

    option_confirmation_score = confirmation.pressure_score if confirmation.status != OptionPressureStatus.BLOCKED else 0.0
    liquidity_score = min(candidate.liquidity_score, confirmation.spread_quality_score, confirmation.depth_quality_score)
    freshness_score = min(candidate.freshness_score, confirmation.freshness_score)

    return replace(
        candidate,
        option_confirmation_score=_bounded(option_confirmation_score),
        liquidity_score=_bounded(liquidity_score),
        freshness_score=_bounded(freshness_score),
        blockers=tuple(_dedupe(blockers)),
        warnings=tuple(_dedupe(warnings)),
        evidence=evidence,
    )


def attach_option_pressure_to_candidates(
    candidates: Iterable[StrategyCandidate],
    context: StrategyContext | None,
) -> tuple[StrategyCandidate, ...]:
    return tuple(attach_option_pressure_confirmation(candidate, context) for candidate in candidates)


def _base_blockers(context: StrategyContext, direction: Direction) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if context.option_ltp_age_sec is None or context.option_ltp_age_sec > 5.0:
        blockers.append("STALE_OPTION_LTP")
    if context.quote_source and context.quote_source.upper() == "FALLBACK":
        blockers.append("FALLBACK_QUOTE_ONLY")

    if direction == Direction.NO_TRADE:
        return blockers, warnings

    spread = context.ce_spread_pct if direction == Direction.BUY_CALL else context.pe_spread_pct
    depth = context.ce_depth if direction == Direction.BUY_CALL else context.pe_depth
    option_ltp = context.option_ce_ltp if direction == Direction.BUY_CALL else context.option_pe_ltp

    if option_ltp is None:
        blockers.append("UNRESOLVED_CONTRACT")
    if spread is None or spread > 3.0:
        blockers.append("WIDE_SPREAD")
    if depth is None or depth <= 0:
        blockers.append("MISSING_DEPTH")

    if context.ce_premium_change is None or context.pe_premium_change is None:
        warnings.append("OPTION_PREMIUM_CHANGE_MISSING")

    return blockers, warnings


def _side_pressure_score(
    *,
    premium_change: float | None,
    spread_pct: float | None,
    depth: float | None,
    option_ltp: float | None,
) -> float:
    if option_ltp is None:
        return 0.0
    premium_score = _bounded(0.35 + max(0.0, _float(premium_change, 0.0)) / 40.0)
    spread_score = _spread_quality(spread_pct)
    depth_score = _depth_quality(depth)
    return _bounded((premium_score * 0.55) + (spread_score * 0.20) + (depth_score * 0.25))


def _directional_pressure_score(
    *,
    direction: Direction,
    ce_pressure: float,
    pe_pressure: float,
    premium_bias: float,
    spread_quality: float,
    depth_quality: float,
    freshness: float,
) -> float:
    if direction == Direction.NO_TRADE:
        return 0.0
    directional_pressure = ce_pressure if direction == Direction.BUY_CALL else pe_pressure
    opposite_pressure = pe_pressure if direction == Direction.BUY_CALL else ce_pressure
    bias_component = max(0.0, premium_bias if direction == Direction.BUY_CALL else -premium_bias)
    contrast = max(0.0, directional_pressure - opposite_pressure)
    return _bounded(
        directional_pressure * 0.45
        + contrast * 0.15
        + bias_component * 0.15
        + spread_quality * 0.10
        + depth_quality * 0.10
        + freshness * 0.05
    )


def _has_conflicting_pressure(direction: Direction, premium_bias: float) -> bool:
    if direction == Direction.BUY_CALL:
        return premium_bias <= -0.12
    if direction == Direction.BUY_PUT:
        return premium_bias >= 0.12
    return False


def _premium_bias(context: StrategyContext) -> float:
    ce = _float(context.ce_premium_change, 0.0)
    pe = _float(context.pe_premium_change, 0.0)
    return max(-1.0, min(1.0, (ce - pe) / 40.0))


def _directional_spread_quality(context: StrategyContext, direction: Direction) -> float:
    if direction == Direction.BUY_CALL:
        return _spread_quality(context.ce_spread_pct)
    if direction == Direction.BUY_PUT:
        return _spread_quality(context.pe_spread_pct)
    return min(_spread_quality(context.ce_spread_pct), _spread_quality(context.pe_spread_pct))


def _directional_depth_quality(context: StrategyContext, direction: Direction) -> float:
    if direction == Direction.BUY_CALL:
        return _depth_quality(context.ce_depth)
    if direction == Direction.BUY_PUT:
        return _depth_quality(context.pe_depth)
    return min(_depth_quality(context.ce_depth), _depth_quality(context.pe_depth))


def _spread_quality(spread_pct: float | None) -> float:
    if spread_pct is None:
        return 0.0
    if spread_pct <= 0.75:
        return 1.0
    if spread_pct <= 1.5:
        return 0.75
    if spread_pct <= 3.0:
        return 0.45
    return 0.0


def _depth_quality(depth: float | None) -> float:
    if depth is None or depth <= 0:
        return 0.0
    if depth >= 500:
        return 1.0
    if depth >= 250:
        return 0.75
    if depth >= 100:
        return 0.45
    return 0.20


def _freshness_score(context: StrategyContext) -> float:
    if context.option_ltp_age_sec is None:
        return 0.0
    return _bounded(1.0 - max(0.0, context.option_ltp_age_sec) / 10.0)


def _evidence(context: StrategyContext) -> dict[str, Any]:
    return {
        "symbol": context.symbol,
        "ts_epoch": context.ts_epoch,
        "option_ce_ltp": context.option_ce_ltp,
        "option_pe_ltp": context.option_pe_ltp,
        "ce_premium_change": context.ce_premium_change,
        "pe_premium_change": context.pe_premium_change,
        "ce_spread_pct": context.ce_spread_pct,
        "pe_spread_pct": context.pe_spread_pct,
        "ce_depth": context.ce_depth,
        "pe_depth": context.pe_depth,
        "option_ltp_age_sec": context.option_ltp_age_sec,
        "quote_source": context.quote_source,
        "is_order_action": False,
    }


def _result(
    *,
    direction: Direction,
    status: OptionPressureStatus,
    pressure_score: float = 0.0,
    ce_pressure_score: float = 0.0,
    pe_pressure_score: float = 0.0,
    premium_bias: float = 0.0,
    spread_quality_score: float = 0.0,
    depth_quality_score: float = 0.0,
    freshness_score: float = 0.0,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    evidence: dict[str, Any] | None = None,
) -> OptionPressureConfirmationResult:
    return OptionPressureConfirmationResult(
        direction=direction,
        status=status,
        pressure_score=_bounded(pressure_score),
        ce_pressure_score=_bounded(ce_pressure_score),
        pe_pressure_score=_bounded(pe_pressure_score),
        premium_bias=round(max(-1.0, min(1.0, float(premium_bias))), 4),
        spread_quality_score=_bounded(spread_quality_score),
        depth_quality_score=_bounded(depth_quality_score),
        freshness_score=_bounded(freshness_score),
        blockers=tuple(_dedupe(blockers or [])),
        warnings=tuple(_dedupe(warnings or [])),
        evidence=dict(evidence or {}),
    )


def _parse_direction(direction: Direction | str) -> Direction:
    try:
        return Direction(str(direction))
    except Exception:
        return Direction.NO_TRADE


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bounded(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out

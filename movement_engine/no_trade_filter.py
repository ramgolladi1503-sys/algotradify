from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Iterable

from movement_engine.contract import CandidateStatus, Direction, StrategyCandidate
from movement_engine.option_pressure import OPTION_PRESSURE_EVIDENCE_KEY, OptionPressureStatus


NO_TRADE_FILTER_EVIDENCE_KEY = "no_trade_filter"

HARD_NO_TRADE_BLOCKERS = (
    "MARKET_CLOSED",
    "STALE_OPTION_LTP",
    "FALLBACK_QUOTE_ONLY",
    "UNRESOLVED_CONTRACT",
    "WIDE_SPREAD",
    "MISSING_DEPTH",
    "CONFLICTING_TRAP_SIGNAL",
    "NO_TRADE_CHOP",
    "EXECUTION_SAFETY_NOT_PERMITTED",
)

WEAK_CONFIRMATION_COMPOUND_BLOCKERS = (
    "NO_TRADE_CHOP",
    "WIDE_SPREAD",
    "MISSING_DEPTH",
    "STALE_OPTION_LTP",
    "FALLBACK_QUOTE_ONLY",
    "CONFLICTING_TRAP_SIGNAL",
)


class NoTradeDecision(StrEnum):
    ALLOW_CANDIDATE = "ALLOW_CANDIDATE"
    BLOCK_CANDIDATE = "BLOCK_CANDIDATE"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True)
class NoTradeFilterResult:
    candidate_id: str
    decision: NoTradeDecision
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    diagnostics: tuple[dict[str, Any], ...] = ()

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "decision": self.decision.value,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class NoTradeFilterSummary:
    input_count: int = 0
    allowed_count: int = 0
    blocked_count: int = 0
    no_trade_count: int = 0

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_count": self.input_count,
            "allowed_count": self.allowed_count,
            "blocked_count": self.blocked_count,
            "no_trade_count": self.no_trade_count,
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class NoTradeFilterBatchResult:
    candidates: tuple[StrategyCandidate, ...]
    results: tuple[NoTradeFilterResult, ...]
    summary: NoTradeFilterSummary
    warnings: tuple[str, ...] = ()
    diagnostics: tuple[dict[str, Any], ...] = ()

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "results": [result.to_dict() for result in self.results],
            "summary": self.summary.to_dict(),
            "warnings": list(self.warnings),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "is_order_action": self.is_order_action,
        }


def apply_no_trade_filter(candidate: StrategyCandidate) -> tuple[StrategyCandidate, NoTradeFilterResult]:
    """Apply read-only no-trade/conflict filtering to one candidate."""

    blockers = list(candidate.blockers)
    warnings = list(candidate.warnings)
    diagnostics: list[dict[str, Any]] = []

    option_status = _option_pressure_status(candidate)
    option_payload = _option_pressure_payload(candidate)

    if candidate.direction == Direction.NO_TRADE:
        blockers.append("NO_TRADE_DIRECTION")
        decision = NoTradeDecision.NO_TRADE
        diagnostics.append(_diagnostic("NO_TRADE_DIRECTION", candidate, "Candidate direction is NO_TRADE."))
    elif candidate.status == CandidateStatus.NO_TRADE:
        blockers.append("NO_TRADE_STATUS")
        decision = NoTradeDecision.NO_TRADE
        diagnostics.append(_diagnostic("NO_TRADE_STATUS", candidate, "Candidate already has NO_TRADE status."))
    elif option_status == OptionPressureStatus.CONFLICTING_PRESSURE.value:
        blockers.extend(["CONFLICTING_OPTION_PRESSURE", "CONFLICTING_TRAP_SIGNAL"])
        decision = NoTradeDecision.BLOCK_CANDIDATE
        diagnostics.append(_diagnostic("CONFLICTING_OPTION_PRESSURE", candidate, "Option pressure conflicts with candidate direction."))
    elif _has_hard_blocker(blockers):
        decision = NoTradeDecision.BLOCK_CANDIDATE
        diagnostics.append(_diagnostic("HARD_NO_TRADE_BLOCKER", candidate, "Candidate contains a hard no-trade blocker."))
    elif option_status == OptionPressureStatus.BLOCKED.value:
        blockers.append("OPTION_PRESSURE_BLOCKED")
        decision = NoTradeDecision.BLOCK_CANDIDATE
        diagnostics.append(_diagnostic("OPTION_PRESSURE_BLOCKED", candidate, "Option pressure confirmation is blocked."))
    elif option_status == OptionPressureStatus.NOT_APPLICABLE.value and candidate.direction != Direction.NO_TRADE:
        blockers.append("OPTION_PRESSURE_NOT_APPLICABLE")
        decision = NoTradeDecision.BLOCK_CANDIDATE
        diagnostics.append(_diagnostic("OPTION_PRESSURE_NOT_APPLICABLE", candidate, "Option pressure is not applicable for this candidate."))
    elif _weak_confirmation_with_bad_context(candidate, blockers, option_payload):
        blockers.append("WEAK_CONFIRMATION_WITH_RISK_CONTEXT")
        decision = NoTradeDecision.BLOCK_CANDIDATE
        diagnostics.append(_diagnostic("WEAK_CONFIRMATION_WITH_RISK_CONTEXT", candidate, "Weak option confirmation is combined with bad liquidity, freshness, or regime context."))
    elif option_status == OptionPressureStatus.WEAK_CONFIRMATION.value:
        warnings.append("WEAK_OPTION_CONFIRMATION_ALLOWED")
        decision = NoTradeDecision.ALLOW_CANDIDATE
        diagnostics.append(_diagnostic("WEAK_OPTION_CONFIRMATION_ALLOWED", candidate, "Weak option confirmation allowed because no compounding no-trade risk was present."))
    else:
        decision = NoTradeDecision.ALLOW_CANDIDATE
        diagnostics.append(_diagnostic("CANDIDATE_ALLOWED", candidate, "Candidate passed no-trade filter."))

    filtered = _apply_decision(candidate, decision, blockers, warnings, diagnostics)
    result = NoTradeFilterResult(
        candidate_id=candidate.candidate_id,
        decision=decision,
        blockers=tuple(_dedupe(blockers)),
        warnings=tuple(_dedupe(warnings)),
        diagnostics=tuple(diagnostics),
    )
    return filtered, result


def apply_no_trade_filter_to_candidates(candidates: Iterable[StrategyCandidate]) -> NoTradeFilterBatchResult:
    raw_candidates = tuple(candidates)
    filtered: list[StrategyCandidate] = []
    results: list[NoTradeFilterResult] = []
    warnings: list[str] = []
    diagnostics: list[dict[str, Any]] = []

    for candidate in raw_candidates:
        filtered_candidate, result = apply_no_trade_filter(candidate)
        filtered.append(filtered_candidate)
        results.append(result)
        warnings.extend(result.warnings)
        diagnostics.extend(result.diagnostics)

    summary = NoTradeFilterSummary(
        input_count=len(raw_candidates),
        allowed_count=sum(1 for result in results if result.decision == NoTradeDecision.ALLOW_CANDIDATE),
        blocked_count=sum(1 for result in results if result.decision == NoTradeDecision.BLOCK_CANDIDATE),
        no_trade_count=sum(1 for result in results if result.decision == NoTradeDecision.NO_TRADE),
    )
    return NoTradeFilterBatchResult(
        candidates=tuple(filtered),
        results=tuple(results),
        summary=summary,
        warnings=tuple(_dedupe(warnings)),
        diagnostics=tuple(diagnostics),
    )


def _apply_decision(
    candidate: StrategyCandidate,
    decision: NoTradeDecision,
    blockers: list[str],
    warnings: list[str],
    diagnostics: list[dict[str, Any]],
) -> StrategyCandidate:
    evidence = dict(candidate.evidence)
    evidence[NO_TRADE_FILTER_EVIDENCE_KEY] = {
        "decision": decision.value,
        "blockers": list(_dedupe(blockers)),
        "warnings": list(_dedupe(warnings)),
        "diagnostics": [dict(item) for item in diagnostics],
        "is_order_action": False,
    }

    if decision == NoTradeDecision.NO_TRADE:
        status = CandidateStatus.NO_TRADE
        direction = Direction.NO_TRADE
    elif decision == NoTradeDecision.BLOCK_CANDIDATE:
        status = CandidateStatus.BLOCKED_CANDIDATE
        direction = candidate.direction
    else:
        status = candidate.status
        direction = candidate.direction

    return replace(
        candidate,
        direction=direction,
        status=status,
        blockers=tuple(_dedupe(blockers)),
        warnings=tuple(_dedupe(warnings)),
        evidence=evidence,
    )


def _option_pressure_payload(candidate: StrategyCandidate) -> dict[str, Any]:
    payload = candidate.evidence.get(OPTION_PRESSURE_EVIDENCE_KEY, {})
    return dict(payload) if isinstance(payload, dict) else {}


def _option_pressure_status(candidate: StrategyCandidate) -> str | None:
    payload = _option_pressure_payload(candidate)
    status = payload.get("status")
    return str(status) if status else None


def _weak_confirmation_with_bad_context(
    candidate: StrategyCandidate,
    blockers: list[str],
    option_payload: dict[str, Any],
) -> bool:
    if option_payload.get("status") != OptionPressureStatus.WEAK_CONFIRMATION.value:
        return False
    if any(blocker in WEAK_CONFIRMATION_COMPOUND_BLOCKERS for blocker in blockers):
        return True
    if candidate.liquidity_score < 0.45:
        return True
    if candidate.freshness_score < 0.45:
        return True
    if candidate.regime_alignment_score < 0.25:
        return True
    if _float(option_payload.get("spread_quality_score"), 1.0) < 0.45:
        return True
    if _float(option_payload.get("depth_quality_score"), 1.0) < 0.45:
        return True
    if _float(option_payload.get("freshness_score"), 1.0) < 0.45:
        return True
    return False


def _has_hard_blocker(blockers: list[str]) -> bool:
    return any(blocker in HARD_NO_TRADE_BLOCKERS for blocker in blockers)


def _diagnostic(code: str, candidate: StrategyCandidate, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "candidate_id": candidate.candidate_id,
        "strategy_id": candidate.strategy_id,
        "message": message,
        "is_order_action": False,
    }


def _float(value: Any, default: float = 0.0) -> float:
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

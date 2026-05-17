from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Iterable

from movement_engine.contract import CandidateStatus, Direction, StrategyCandidate
from movement_engine.no_trade_filter import NO_TRADE_FILTER_EVIDENCE_KEY, NoTradeDecision


RANKER_EVIDENCE_KEY = "movement_ranker"

RANKABLE_STATUSES = (
    CandidateStatus.RAW_CANDIDATE,
    CandidateStatus.VALIDATED_CANDIDATE,
    CandidateStatus.RANKED_OPPORTUNITY,
)


class RankExclusionReason(StrEnum):
    BLOCKED_CANDIDATE = "BLOCKED_CANDIDATE"
    NO_TRADE = "NO_TRADE"
    NOT_ALLOWED_BY_NO_TRADE_FILTER = "NOT_ALLOWED_BY_NO_TRADE_FILTER"
    UNRANKABLE_STATUS = "UNRANKABLE_STATUS"


@dataclass(frozen=True)
class CandidateRankRecord:
    candidate_id: str
    strategy_id: str
    rank: int
    rank_score: float
    component_scores: dict[str, float]
    tie_breaker: tuple[Any, ...]

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "rank": self.rank,
            "rank_score": self.rank_score,
            "component_scores": dict(self.component_scores),
            "tie_breaker": list(self.tie_breaker),
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class CandidateRankExclusion:
    candidate_id: str
    strategy_id: str
    reason: RankExclusionReason
    status: str
    blockers: tuple[str, ...] = ()

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "reason": self.reason.value,
            "status": self.status,
            "blockers": list(self.blockers),
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class MovementRankSummary:
    input_count: int = 0
    ranked_count: int = 0
    excluded_count: int = 0
    blocked_count: int = 0
    no_trade_count: int = 0
    top_candidate_id: str | None = None

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_count": self.input_count,
            "ranked_count": self.ranked_count,
            "excluded_count": self.excluded_count,
            "blocked_count": self.blocked_count,
            "no_trade_count": self.no_trade_count,
            "top_candidate_id": self.top_candidate_id,
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class MovementRankResult:
    ranked_candidates: tuple[StrategyCandidate, ...]
    rank_records: tuple[CandidateRankRecord, ...]
    exclusions: tuple[CandidateRankExclusion, ...]
    summary: MovementRankSummary
    warnings: tuple[str, ...] = ()
    diagnostics: tuple[dict[str, Any], ...] = ()

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ranked_candidates": [candidate.to_dict() for candidate in self.ranked_candidates],
            "rank_records": [record.to_dict() for record in self.rank_records],
            "exclusions": [exclusion.to_dict() for exclusion in self.exclusions],
            "summary": self.summary.to_dict(),
            "warnings": list(self.warnings),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "is_order_action": self.is_order_action,
        }


def rank_movement_candidates(candidates: Iterable[StrategyCandidate] | None) -> MovementRankResult:
    """Rank allowed movement candidates without creating execution intent."""

    raw_candidates = tuple(candidates or ())
    rankable: list[StrategyCandidate] = []
    exclusions: list[CandidateRankExclusion] = []
    warnings: list[str] = []
    diagnostics: list[dict[str, Any]] = []

    for candidate in raw_candidates:
        exclusion = _rank_exclusion(candidate)
        if exclusion is not None:
            exclusions.append(exclusion)
            diagnostics.append(_diagnostic("RANK_EXCLUDED", candidate, f"Candidate excluded from ranker: {exclusion.reason.value}"))
            continue
        rankable.append(candidate)

    scored = sorted(
        ((_rank_score(candidate), candidate) for candidate in rankable),
        key=lambda item: _sort_key(item[0], item[1]),
    )

    ranked_candidates: list[StrategyCandidate] = []
    rank_records: list[CandidateRankRecord] = []

    for index, (rank_score, candidate) in enumerate(scored, start=1):
        record = CandidateRankRecord(
            candidate_id=candidate.candidate_id,
            strategy_id=candidate.strategy_id,
            rank=index,
            rank_score=rank_score,
            component_scores=_component_scores(candidate),
            tie_breaker=_tie_breaker(candidate),
        )
        ranked_candidates.append(_attach_rank(candidate, record))
        rank_records.append(record)

    if not ranked_candidates and raw_candidates:
        warnings.append("NO_RANKABLE_CANDIDATES")

    summary = MovementRankSummary(
        input_count=len(raw_candidates),
        ranked_count=len(ranked_candidates),
        excluded_count=len(exclusions),
        blocked_count=sum(1 for candidate in raw_candidates if candidate.status == CandidateStatus.BLOCKED_CANDIDATE),
        no_trade_count=sum(1 for candidate in raw_candidates if candidate.status == CandidateStatus.NO_TRADE or candidate.direction == Direction.NO_TRADE),
        top_candidate_id=ranked_candidates[0].candidate_id if ranked_candidates else None,
    )

    return MovementRankResult(
        ranked_candidates=tuple(ranked_candidates),
        rank_records=tuple(rank_records),
        exclusions=tuple(exclusions),
        summary=summary,
        warnings=tuple(_dedupe(warnings)),
        diagnostics=tuple(diagnostics),
    )


def _rank_exclusion(candidate: StrategyCandidate) -> CandidateRankExclusion | None:
    if candidate.status == CandidateStatus.BLOCKED_CANDIDATE:
        return _exclusion(candidate, RankExclusionReason.BLOCKED_CANDIDATE)
    if candidate.status == CandidateStatus.NO_TRADE or candidate.direction == Direction.NO_TRADE:
        return _exclusion(candidate, RankExclusionReason.NO_TRADE)
    if candidate.status not in RANKABLE_STATUSES:
        return _exclusion(candidate, RankExclusionReason.UNRANKABLE_STATUS)
    if _no_trade_decision(candidate) != NoTradeDecision.ALLOW_CANDIDATE.value:
        return _exclusion(candidate, RankExclusionReason.NOT_ALLOWED_BY_NO_TRADE_FILTER)
    return None


def _exclusion(candidate: StrategyCandidate, reason: RankExclusionReason) -> CandidateRankExclusion:
    return CandidateRankExclusion(
        candidate_id=candidate.candidate_id,
        strategy_id=candidate.strategy_id,
        reason=reason,
        status=candidate.status.value,
        blockers=tuple(candidate.blockers),
    )


def _rank_score(candidate: StrategyCandidate) -> float:
    scores = _component_scores(candidate)
    total = (
        scores["raw_score"] * 0.18
        + scores["confidence_score"] * 0.18
        + scores["option_confirmation_score"] * 0.20
        + scores["liquidity_score"] * 0.14
        + scores["freshness_score"] * 0.12
        + scores["volatility_score"] * 0.08
        + scores["regime_alignment_score"] * 0.10
    )
    return _bounded(total)


def _component_scores(candidate: StrategyCandidate) -> dict[str, float]:
    return {
        "raw_score": _bounded(candidate.raw_score),
        "confidence_score": _bounded(candidate.confidence_score),
        "option_confirmation_score": _bounded(candidate.option_confirmation_score),
        "liquidity_score": _bounded(candidate.liquidity_score),
        "freshness_score": _bounded(candidate.freshness_score),
        "volatility_score": _bounded(candidate.volatility_score),
        "regime_alignment_score": _bounded(candidate.regime_alignment_score),
    }


def _sort_key(rank_score: float, candidate: StrategyCandidate) -> tuple[Any, ...]:
    tie_breaker = _tie_breaker(candidate)
    return (-rank_score, *tie_breaker)


def _tie_breaker(candidate: StrategyCandidate) -> tuple[Any, ...]:
    return (
        -_bounded(candidate.option_confirmation_score),
        -_bounded(candidate.liquidity_score),
        -_bounded(candidate.freshness_score),
        -_bounded(candidate.regime_alignment_score),
        candidate.strategy_id,
        candidate.candidate_id,
    )


def _attach_rank(candidate: StrategyCandidate, record: CandidateRankRecord) -> StrategyCandidate:
    evidence = dict(candidate.evidence)
    evidence[RANKER_EVIDENCE_KEY] = record.to_dict()
    return replace(
        candidate,
        status=CandidateStatus.RANKED_OPPORTUNITY,
        evidence=evidence,
    )


def _no_trade_decision(candidate: StrategyCandidate) -> str | None:
    payload = candidate.evidence.get(NO_TRADE_FILTER_EVIDENCE_KEY, {})
    if not isinstance(payload, dict):
        return None
    decision = payload.get("decision")
    return str(decision) if decision else None


def _diagnostic(code: str, candidate: StrategyCandidate, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "candidate_id": candidate.candidate_id,
        "strategy_id": candidate.strategy_id,
        "message": message,
        "is_order_action": False,
    }


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

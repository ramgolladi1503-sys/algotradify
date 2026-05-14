from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from candidate_truth import CandidateTruthRecord, CandidateTruthStatus, normalize_candidates


class OpportunityStatus(StrEnum):
    SELECTED = "SELECTED"
    RANKED = "RANKED"
    BLOCKED = "BLOCKED"
    DROPPED = "DROPPED"


_NON_RANKABLE_TRUTH_STATUSES = {
    CandidateTruthStatus.MALFORMED,
    CandidateTruthStatus.SYNTHETIC,
    CandidateTruthStatus.UNKNOWN,
}


@dataclass(frozen=True)
class OpportunityRecord:
    candidate_id: str
    symbol: str | None
    strategy_id: str | None
    setup_family: str | None
    truth_status: str
    opportunity_status: OpportunityStatus
    rank_score: float
    rank: int | None = None
    selected: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    candidate_truth: dict[str, Any] = field(default_factory=dict)

    @property
    def is_execution_decision(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "strategy_id": self.strategy_id,
            "setup_family": self.setup_family,
            "truth_status": self.truth_status,
            "opportunity_status": self.opportunity_status.value,
            "rank_score": self.rank_score,
            "rank": self.rank,
            "selected": self.selected,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "provenance": dict(self.provenance),
            "candidate_truth": dict(self.candidate_truth),
            "is_execution_decision": self.is_execution_decision,
        }


@dataclass(frozen=True)
class OpportunityLayerResult:
    status: str
    reason: str | None
    counts: dict[str, int]
    selected: OpportunityRecord | None
    ranked: list[OpportunityRecord]
    blocked: list[OpportunityRecord]
    dropped: list[OpportunityRecord]
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def is_execution_decision(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "counts": dict(self.counts),
            "selected": self.selected.to_dict() if self.selected else None,
            "ranked": [row.to_dict() for row in self.ranked],
            "blocked": [row.to_dict() for row in self.blocked],
            "dropped": [row.to_dict() for row in self.dropped],
            "diagnostics": dict(self.diagnostics),
            "is_execution_decision": self.is_execution_decision,
        }


def _base_score(record: CandidateTruthRecord) -> float:
    normalized = record.normalized or {}
    raw = record.raw or {}
    value = normalized.get("score")
    if value is None:
        value = normalized.get("confidence")
    if value is None:
        value = raw.get("score") or raw.get("final_score") or raw.get("rank_score") or raw.get("confidence")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _make_opportunity_record(
    record: CandidateTruthRecord,
    *,
    status: OpportunityStatus,
    rank_score: float = 0.0,
    rank: int | None = None,
    selected: bool = False,
    extra_blockers: list[str] | None = None,
) -> OpportunityRecord:
    blockers = list(record.blockers)
    if extra_blockers:
        blockers.extend(extra_blockers)
    return OpportunityRecord(
        candidate_id=record.candidate_id,
        symbol=record.symbol,
        strategy_id=record.strategy_id,
        setup_family=record.setup_family,
        truth_status=record.truth_status.value,
        opportunity_status=status,
        rank_score=rank_score,
        rank=rank,
        selected=selected,
        blockers=blockers,
        warnings=list(record.warnings),
        provenance=dict(record.provenance),
        candidate_truth=record.to_dict(),
    )


def _classify_survival(records: list[CandidateTruthRecord]) -> tuple[list[CandidateTruthRecord], list[OpportunityRecord], list[OpportunityRecord]]:
    rankable: list[CandidateTruthRecord] = []
    blocked: list[OpportunityRecord] = []
    dropped: list[OpportunityRecord] = []

    for record in records:
        if record.truth_status in _NON_RANKABLE_TRUTH_STATUSES:
            dropped.append(
                _make_opportunity_record(
                    record,
                    status=OpportunityStatus.DROPPED,
                    extra_blockers=[f"NON_RANKABLE_TRUTH_STATUS:{record.truth_status.value}"],
                )
            )
            continue
        if record.blockers:
            blocked.append(_make_opportunity_record(record, status=OpportunityStatus.BLOCKED, rank_score=_base_score(record)))
            continue
        rankable.append(record)

    return rankable, blocked, dropped


def run_opportunity_pipeline(candidates: list[Any], *, source: str = "unknown", select_top: bool = True) -> OpportunityLayerResult:
    truth_records = normalize_candidates(candidates, source=source)
    raw_count = len(candidates)
    truth_count = len(truth_records)

    rankable, blocked, dropped = _classify_survival(truth_records)

    ranked_records: list[OpportunityRecord] = []
    for index, record in enumerate(sorted(rankable, key=_base_score, reverse=True), start=1):
        ranked_records.append(
            _make_opportunity_record(
                record,
                status=OpportunityStatus.RANKED,
                rank_score=_base_score(record),
                rank=index,
            )
        )

    selected: OpportunityRecord | None = None
    if select_top and ranked_records:
        top = ranked_records[0]
        selected = OpportunityRecord(
            candidate_id=top.candidate_id,
            symbol=top.symbol,
            strategy_id=top.strategy_id,
            setup_family=top.setup_family,
            truth_status=top.truth_status,
            opportunity_status=OpportunityStatus.SELECTED,
            rank_score=top.rank_score,
            rank=top.rank,
            selected=True,
            blockers=list(top.blockers),
            warnings=list(top.warnings),
            provenance=dict(top.provenance),
            candidate_truth=dict(top.candidate_truth),
        )

    counts = {
        "raw_count": raw_count,
        "truth_count": truth_count,
        "rankable_count": len(rankable),
        "ranked_count": len(ranked_records),
        "blocked_count": len(blocked),
        "dropped_count": len(dropped),
        "selected_count": 1 if selected else 0,
    }

    if raw_count == 0:
        status = "NO_CANDIDATES"
        reason = "raw_count=0"
    elif not ranked_records:
        status = "NO_RANKABLE_CANDIDATES"
        reason = "no_execution_candidates"
    else:
        status = "OPPORTUNITIES_AVAILABLE"
        reason = None

    diagnostics = {
        "pipeline": "normalize -> classify -> rank -> select -> emit",
        "source": source,
        "blocked_reasons": _reason_counts(blocked),
        "dropped_reasons": _reason_counts(dropped),
    }

    return OpportunityLayerResult(
        status=status,
        reason=reason,
        counts=counts,
        selected=selected,
        ranked=ranked_records,
        blocked=blocked,
        dropped=dropped,
        diagnostics=diagnostics,
    )


def _reason_counts(records: list[OpportunityRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        reasons = record.blockers or [record.opportunity_status.value]
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return counts

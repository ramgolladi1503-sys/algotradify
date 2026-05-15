from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TopExecutableSelectorStatus(StrEnum):
    SELECTED = "SELECTED"
    NO_ELIGIBLE_CANDIDATES = "NO_ELIGIBLE_CANDIDATES"


@dataclass(frozen=True)
class TopExecutableSelection:
    status: TopExecutableSelectorStatus
    selected: dict[str, Any] | None
    eligible: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    reason: str | None = None

    @property
    def is_order(self) -> bool:
        return False

    @property
    def is_selector_decision(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "selected": dict(self.selected) if self.selected else None,
            "eligible": [dict(row) for row in self.eligible],
            "rejected": [dict(row) for row in self.rejected],
            "reason": self.reason,
            "is_order": self.is_order,
            "is_selector_decision": self.is_selector_decision,
        }


def select_top_executable(
    trade_quality_rows: list[dict[str, Any]],
    *,
    min_quality_score: float = 50.0,
) -> TopExecutableSelection:
    eligible: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for row in trade_quality_rows:
        rejection_reasons = _rejection_reasons(row, min_quality_score=min_quality_score)
        enriched = dict(row)
        if rejection_reasons:
            enriched["selector_rejection_reasons"] = rejection_reasons
            rejected.append(enriched)
        else:
            eligible.append(enriched)

    eligible.sort(key=lambda row: (_score(row), str(row.get("candidate_id") or "")), reverse=True)
    for index, row in enumerate(eligible, start=1):
        row["selector_rank"] = index

    if not eligible:
        return TopExecutableSelection(
            status=TopExecutableSelectorStatus.NO_ELIGIBLE_CANDIDATES,
            selected=None,
            eligible=[],
            rejected=rejected,
            reason="no_execution_allowed_quality_candidate",
        )

    selected = dict(eligible[0])
    selected["selected_by"] = "top_executable_selector"
    selected["selection_reason"] = "highest_quality_score_above_threshold"

    return TopExecutableSelection(
        status=TopExecutableSelectorStatus.SELECTED,
        selected=selected,
        eligible=eligible,
        rejected=rejected,
        reason="selected_highest_quality_candidate",
    )


def _rejection_reasons(row: dict[str, Any], *, min_quality_score: float) -> list[str]:
    reasons: list[str] = []
    execution = row.get("execution_readiness") or {}
    if not execution.get("execution_allowed"):
        reasons.append("EXECUTION_NOT_ALLOWED")
    if _score(row) < min_quality_score:
        reasons.append("QUALITY_SCORE_BELOW_THRESHOLD")
    if row.get("status") == "BLOCKED_NOT_EXECUTION_READY":
        reasons.append("TRADE_QUALITY_BLOCKED")
    blockers = row.get("blockers") or []
    if blockers:
        reasons.extend([f"BLOCKER:{blocker}" for blocker in blockers])
    return _dedupe(reasons)


def _score(row: dict[str, Any]) -> float:
    try:
        return float(row.get("quality_score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

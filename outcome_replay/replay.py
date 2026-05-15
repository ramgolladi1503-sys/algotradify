from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class OutcomeStatus(StrEnum):
    SELECTED = "SELECTED"
    BLOCKED = "BLOCKED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    EXITED = "EXITED"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


_TERMINAL_OUTCOMES = {
    OutcomeStatus.REJECTED,
    OutcomeStatus.FILLED,
    OutcomeStatus.EXITED,
    OutcomeStatus.CLOSED,
}

_STATUS_ALIASES = {
    "SELECTED": OutcomeStatus.SELECTED,
    "TOP_EXECUTABLE_SELECTED": OutcomeStatus.SELECTED,
    "BLOCKED": OutcomeStatus.BLOCKED,
    "NO_ELIGIBLE_CANDIDATES": OutcomeStatus.BLOCKED,
    "ORDER_SUBMITTED": OutcomeStatus.SUBMITTED,
    "SUBMITTED": OutcomeStatus.SUBMITTED,
    "ORDER_ACCEPTED": OutcomeStatus.ACCEPTED,
    "ACCEPTED": OutcomeStatus.ACCEPTED,
    "OPEN": OutcomeStatus.ACCEPTED,
    "ORDER_REJECTED": OutcomeStatus.REJECTED,
    "REJECTED": OutcomeStatus.REJECTED,
    "PARTIALLY_FILLED": OutcomeStatus.PARTIALLY_FILLED,
    "PARTIAL": OutcomeStatus.PARTIALLY_FILLED,
    "FILLED": OutcomeStatus.FILLED,
    "COMPLETE": OutcomeStatus.FILLED,
    "EXIT_FILLED": OutcomeStatus.EXITED,
    "EXITED": OutcomeStatus.EXITED,
    "POSITION_CLOSED": OutcomeStatus.CLOSED,
    "CLOSED": OutcomeStatus.CLOSED,
}


@dataclass(frozen=True)
class OutcomeEvent:
    candidate_id: str
    status: OutcomeStatus
    ts_epoch: float | None = None
    source: str = "runtime_artifact"
    reason: str | None = None
    quality_score: float | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status.value,
            "ts_epoch": self.ts_epoch,
            "source": self.source,
            "reason": self.reason,
            "quality_score": self.quality_score,
            "evidence": dict(self.evidence),
            "raw": dict(self.raw),
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class OutcomeReplaySummary:
    candidate_id: str
    current_status: OutcomeStatus
    events: list[OutcomeEvent]
    terminal: bool
    selected_count: int
    blocked_count: int
    filled_count: int
    rejected_count: int
    best_quality_score: float | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "current_status": self.current_status.value,
            "terminal": self.terminal,
            "selected_count": self.selected_count,
            "blocked_count": self.blocked_count,
            "filled_count": self.filled_count,
            "rejected_count": self.rejected_count,
            "best_quality_score": self.best_quality_score,
            "events": [event.to_dict() for event in self.events],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "is_order_action": self.is_order_action,
        }


def normalize_outcome_replay(records: list[dict[str, Any]], *, candidate_id: str | None = None) -> OutcomeReplaySummary:
    events = [_event_from_record(row) for row in records if isinstance(row, dict)]
    if candidate_id:
        events = [event for event in events if event.candidate_id == candidate_id]
    events.sort(key=lambda event: (event.ts_epoch is None, event.ts_epoch or 0.0))

    resolved_candidate_id = candidate_id or _first_candidate_id(events) or "unknown"
    if not events:
        return OutcomeReplaySummary(
            candidate_id=resolved_candidate_id,
            current_status=OutcomeStatus.UNKNOWN,
            events=[],
            terminal=False,
            selected_count=0,
            blocked_count=0,
            filled_count=0,
            rejected_count=0,
            blockers=["NO_OUTCOME_EVENTS"],
        )

    latest = events[-1]
    return OutcomeReplaySummary(
        candidate_id=resolved_candidate_id,
        current_status=latest.status,
        events=events,
        terminal=latest.status in _TERMINAL_OUTCOMES,
        selected_count=sum(1 for event in events if event.status == OutcomeStatus.SELECTED),
        blocked_count=sum(1 for event in events if event.status == OutcomeStatus.BLOCKED),
        filled_count=sum(1 for event in events if event.status == OutcomeStatus.FILLED),
        rejected_count=sum(1 for event in events if event.status == OutcomeStatus.REJECTED),
        best_quality_score=_best_quality(events),
        blockers=[] if latest.status != OutcomeStatus.UNKNOWN else ["UNKNOWN_OUTCOME_STATUS"],
        warnings=_warnings(events),
    )


def _event_from_record(row: dict[str, Any]) -> OutcomeEvent:
    status = _normalize_status(row.get("outcome_status") or row.get("status") or row.get("event") or row.get("current_status"))
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    return OutcomeEvent(
        candidate_id=str(row.get("candidate_id") or row.get("trade_id") or row.get("client_order_id") or "unknown"),
        status=status,
        ts_epoch=_num(row.get("ts_epoch") or row.get("timestamp") or row.get("time")),
        source=str(row.get("source") or "runtime_artifact"),
        reason=_str_or_none(row.get("reason") or row.get("message") or row.get("rejection_reason") or row.get("selection_reason")),
        quality_score=_num(row.get("quality_score")),
        evidence=evidence,
        raw=dict(row),
    )


def _normalize_status(value: Any) -> OutcomeStatus:
    key = str(value or "").upper().strip().replace(" ", "_").replace("-", "_")
    return _STATUS_ALIASES.get(key, OutcomeStatus.UNKNOWN)


def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _first_candidate_id(events: list[OutcomeEvent]) -> str | None:
    for event in events:
        if event.candidate_id != "unknown":
            return event.candidate_id
    return None


def _best_quality(events: list[OutcomeEvent]) -> float | None:
    scores = [event.quality_score for event in events if event.quality_score is not None]
    return max(scores) if scores else None


def _warnings(events: list[OutcomeEvent]) -> list[str]:
    warnings: list[str] = []
    if any(event.status == OutcomeStatus.UNKNOWN for event in events):
        warnings.append("UNKNOWN_OUTCOME_EVENT_PRESENT")
    if any(event.candidate_id == "unknown" for event in events):
        warnings.append("UNKNOWN_CANDIDATE_EVENT_PRESENT")
    return warnings

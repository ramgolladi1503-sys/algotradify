from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class FillLifecycleStatus(StrEnum):
    ORDER_INTENT_CREATED = "ORDER_INTENT_CREATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXIT_SUBMITTED = "EXIT_SUBMITTED"
    EXIT_FILLED = "EXIT_FILLED"
    POSITION_CLOSED = "POSITION_CLOSED"
    UNKNOWN = "UNKNOWN"


_TERMINAL_STATUSES = {
    FillLifecycleStatus.ORDER_REJECTED,
    FillLifecycleStatus.CANCELLED,
    FillLifecycleStatus.POSITION_CLOSED,
}

_STATUS_ALIASES = {
    "INTENT": FillLifecycleStatus.ORDER_INTENT_CREATED,
    "ORDER_INTENT": FillLifecycleStatus.ORDER_INTENT_CREATED,
    "ORDER_INTENT_CREATED": FillLifecycleStatus.ORDER_INTENT_CREATED,
    "SUBMITTED": FillLifecycleStatus.ORDER_SUBMITTED,
    "ORDER_SUBMITTED": FillLifecycleStatus.ORDER_SUBMITTED,
    "OPEN": FillLifecycleStatus.ORDER_ACCEPTED,
    "ACCEPTED": FillLifecycleStatus.ORDER_ACCEPTED,
    "ORDER_ACCEPTED": FillLifecycleStatus.ORDER_ACCEPTED,
    "REJECTED": FillLifecycleStatus.ORDER_REJECTED,
    "ORDER_REJECTED": FillLifecycleStatus.ORDER_REJECTED,
    "PARTIAL": FillLifecycleStatus.PARTIALLY_FILLED,
    "PARTIALLY_FILLED": FillLifecycleStatus.PARTIALLY_FILLED,
    "FILLED": FillLifecycleStatus.FILLED,
    "COMPLETE": FillLifecycleStatus.FILLED,
    "CANCELLED": FillLifecycleStatus.CANCELLED,
    "CANCELED": FillLifecycleStatus.CANCELLED,
    "EXIT_SUBMITTED": FillLifecycleStatus.EXIT_SUBMITTED,
    "EXIT_FILLED": FillLifecycleStatus.EXIT_FILLED,
    "POSITION_CLOSED": FillLifecycleStatus.POSITION_CLOSED,
    "CLOSED": FillLifecycleStatus.POSITION_CLOSED,
}


@dataclass(frozen=True)
class FillLifecycleEvent:
    candidate_id: str
    status: FillLifecycleStatus
    ts_epoch: float | None = None
    order_id: str | None = None
    broker_order_id: str | None = None
    quantity: int | float | None = None
    filled_quantity: int | float | None = None
    average_price: float | None = None
    reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_order_submission(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status.value,
            "ts_epoch": self.ts_epoch,
            "order_id": self.order_id,
            "broker_order_id": self.broker_order_id,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "average_price": self.average_price,
            "reason": self.reason,
            "raw": dict(self.raw),
            "is_order_submission": self.is_order_submission,
        }


@dataclass(frozen=True)
class FillLifecycleState:
    candidate_id: str
    current_status: FillLifecycleStatus
    events: list[FillLifecycleEvent]
    terminal: bool
    filled_quantity: int | float | None = None
    average_price: float | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_order_submission(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "current_status": self.current_status.value,
            "terminal": self.terminal,
            "filled_quantity": self.filled_quantity,
            "average_price": self.average_price,
            "events": [event.to_dict() for event in self.events],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "is_order_submission": self.is_order_submission,
        }


def normalize_fill_lifecycle(records: list[dict[str, Any]], *, candidate_id: str | None = None) -> FillLifecycleState:
    events = [_event_from_record(row) for row in records if isinstance(row, dict)]
    if candidate_id:
        events = [event for event in events if event.candidate_id == candidate_id]
    events.sort(key=lambda event: (event.ts_epoch is None, event.ts_epoch or 0.0))

    resolved_candidate_id = candidate_id or _first_candidate_id(events) or "unknown"
    if not events:
        return FillLifecycleState(
            candidate_id=resolved_candidate_id,
            current_status=FillLifecycleStatus.UNKNOWN,
            events=[],
            terminal=False,
            blockers=["NO_FILL_LIFECYCLE_EVENTS"],
        )

    latest = events[-1]
    return FillLifecycleState(
        candidate_id=resolved_candidate_id,
        current_status=latest.status,
        events=events,
        terminal=latest.status in _TERMINAL_STATUSES,
        filled_quantity=_latest_value(events, "filled_quantity"),
        average_price=_latest_value(events, "average_price"),
        blockers=[] if latest.status != FillLifecycleStatus.UNKNOWN else ["UNKNOWN_FILL_LIFECYCLE_STATUS"],
        warnings=_warnings(events),
    )


def _event_from_record(row: dict[str, Any]) -> FillLifecycleEvent:
    status = _normalize_status(row.get("status") or row.get("order_status") or row.get("event") or row.get("lifecycle_status"))
    return FillLifecycleEvent(
        candidate_id=str(row.get("candidate_id") or row.get("trade_id") or row.get("client_order_id") or "unknown"),
        status=status,
        ts_epoch=_num(row.get("ts_epoch") or row.get("timestamp") or row.get("time")),
        order_id=_str_or_none(row.get("order_id") or row.get("client_order_id")),
        broker_order_id=_str_or_none(row.get("broker_order_id") or row.get("exchange_order_id")),
        quantity=_num(row.get("quantity") or row.get("qty")),
        filled_quantity=_num(row.get("filled_quantity") or row.get("filled_qty") or row.get("filled")),
        average_price=_num(row.get("average_price") or row.get("avg_price") or row.get("fill_price")),
        reason=_str_or_none(row.get("reason") or row.get("message") or row.get("rejection_reason")),
        raw=dict(row),
    )


def _normalize_status(value: Any) -> FillLifecycleStatus:
    key = str(value or "").upper().strip().replace(" ", "_").replace("-", "_")
    return _STATUS_ALIASES.get(key, FillLifecycleStatus.UNKNOWN)


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


def _first_candidate_id(events: list[FillLifecycleEvent]) -> str | None:
    for event in events:
        if event.candidate_id != "unknown":
            return event.candidate_id
    return None


def _latest_value(events: list[FillLifecycleEvent], field_name: str) -> Any:
    for event in reversed(events):
        value = getattr(event, field_name)
        if value is not None:
            return value
    return None


def _warnings(events: list[FillLifecycleEvent]) -> list[str]:
    warnings: list[str] = []
    if any(event.status == FillLifecycleStatus.UNKNOWN for event in events):
        warnings.append("UNKNOWN_STATUS_EVENT_PRESENT")
    if any(event.candidate_id == "unknown" for event in events):
        warnings.append("UNKNOWN_CANDIDATE_EVENT_PRESENT")
    return warnings

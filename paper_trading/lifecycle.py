from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any


PAPER_ORDER_LIFECYCLE_SCHEMA_VERSION = "1.0"
TERMINAL_PAPER_ORDER_STATES = {"FILLED", "REJECTED", "CANCELLED", "EXPIRED"}
VALID_PAPER_ORDER_STATES = {
    "CREATED",
    "ACCEPTED",
    "OPEN",
    "PARTIALLY_FILLED",
    "FILLED",
    "REJECTED",
    "CANCELLED",
    "EXPIRED",
}
VALID_TRANSITIONS = {
    None: {"CREATED"},
    "CREATED": {"ACCEPTED", "REJECTED", "CANCELLED", "EXPIRED"},
    "ACCEPTED": {"OPEN", "REJECTED", "CANCELLED", "EXPIRED"},
    "OPEN": {"PARTIALLY_FILLED", "FILLED", "CANCELLED", "EXPIRED", "REJECTED"},
    "PARTIALLY_FILLED": {"PARTIALLY_FILLED", "FILLED", "CANCELLED", "EXPIRED"},
    "FILLED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
    "EXPIRED": set(),
}


class PaperOrderLifecycleStatus(StrEnum):
    CREATED = "CREATED"
    ACCEPTED = "ACCEPTED"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class PaperOrderLifecycleEvent:
    paper_order_id: str
    paper_order_intent_id: str
    candidate_id: str
    status: PaperOrderLifecycleStatus
    ts_epoch: float | None = None
    reason: str | None = None
    filled_quantity: int = 0
    remaining_quantity: int | None = None
    average_fill_price: float | None = None
    event_sequence: int = 1
    source: str = "paper_order_lifecycle"
    intent_snapshot: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def paper_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    @property
    def broker_api_called(self) -> bool:
        return False

    @property
    def real_order_id(self) -> None:
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PAPER_ORDER_LIFECYCLE_SCHEMA_VERSION,
            "event_type": "PAPER_ORDER_LIFECYCLE_EVENT",
            "paper_order_id": self.paper_order_id,
            "paper_order_intent_id": self.paper_order_intent_id,
            "candidate_id": self.candidate_id,
            "status": self.status.value,
            "terminal": self.status.value in TERMINAL_PAPER_ORDER_STATES,
            "ts_epoch": self.ts_epoch,
            "reason": self.reason,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "average_fill_price": self.average_fill_price,
            "event_sequence": self.event_sequence,
            "source": self.source,
            "intent_snapshot": dict(self.intent_snapshot),
            "evidence": dict(self.evidence),
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


@dataclass(frozen=True)
class PaperOrderLifecycleResult:
    created: bool
    event: PaperOrderLifecycleEvent | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    previous_status: str | None = None
    requested_status: str | None = None
    schema_version: str = PAPER_ORDER_LIFECYCLE_SCHEMA_VERSION

    @property
    def paper_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    @property
    def broker_api_called(self) -> bool:
        return False

    @property
    def real_order_id(self) -> None:
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lifecycle_type": "PAPER_ORDER_LIFECYCLE",
            "created": self.created,
            "event": self.event.to_dict() if self.event else None,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "previous_status": self.previous_status,
            "requested_status": self.requested_status,
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_order_lifecycle_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_ORDER_LIFECYCLE_SCHEMA_VERSION,
        "lifecycle_type": "PAPER_ORDER_LIFECYCLE",
        "event_type": "PAPER_ORDER_LIFECYCLE_EVENT",
        "states": sorted(VALID_PAPER_ORDER_STATES),
        "terminal_states": sorted(TERMINAL_PAPER_ORDER_STATES),
        "valid_transitions": {
            str(key) if key is not None else "NONE": sorted(value)
            for key, value in VALID_TRANSITIONS.items()
        },
        "required_result_keys": [
            "schema_version",
            "lifecycle_type",
            "created",
            "event",
            "blockers",
            "warnings",
            "previous_status",
            "requested_status",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_event_keys": [
            "schema_version",
            "event_type",
            "paper_order_id",
            "paper_order_intent_id",
            "candidate_id",
            "status",
            "terminal",
            "filled_quantity",
            "remaining_quantity",
            "average_fill_price",
            "intent_snapshot",
            "evidence",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "safe_flags": {
            "paper_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
    }


def build_paper_order_lifecycle_event(
    *,
    intent: dict[str, Any] | None,
    requested_status: str | PaperOrderLifecycleStatus,
    previous_event: dict[str, Any] | PaperOrderLifecycleEvent | None = None,
    ts_epoch: float | None = None,
    reason: str | None = None,
    filled_quantity: int | None = None,
    average_fill_price: float | None = None,
) -> PaperOrderLifecycleResult:
    status = _coerce_status(requested_status)
    previous_status = _previous_status(previous_event)
    blockers, warnings = validate_paper_order_lifecycle_transition(
        intent=intent,
        requested_status=status.value if status else str(requested_status),
        previous_status=previous_status,
        filled_quantity=filled_quantity,
    )
    if blockers or status is None:
        return PaperOrderLifecycleResult(
            created=False,
            blockers=blockers or ["INVALID_PAPER_ORDER_STATUS"],
            warnings=warnings,
            previous_status=previous_status,
            requested_status=status.value if status else str(requested_status),
        )

    intent_payload = dict(intent or {})
    quantity = _int_or_none(intent_payload.get("quantity")) or 0
    next_filled_quantity = _filled_quantity(status=status, previous_event=previous_event, requested_filled_quantity=filled_quantity, quantity=quantity)
    remaining_quantity = max(quantity - next_filled_quantity, 0) if quantity else 0
    paper_order_id = _stable_paper_order_id(str(intent_payload.get("paper_order_intent_id")), str(intent_payload.get("candidate_id")))
    event_sequence = _previous_sequence(previous_event) + 1
    event = PaperOrderLifecycleEvent(
        paper_order_id=paper_order_id,
        paper_order_intent_id=str(intent_payload.get("paper_order_intent_id")),
        candidate_id=str(intent_payload.get("candidate_id")),
        status=status,
        ts_epoch=ts_epoch,
        reason=reason,
        filled_quantity=next_filled_quantity,
        remaining_quantity=remaining_quantity,
        average_fill_price=_float_or_none(average_fill_price),
        event_sequence=event_sequence,
        intent_snapshot=intent_payload,
        evidence={
            "previous_status": previous_status,
            "requested_status": status.value,
            "paper_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
    )
    return PaperOrderLifecycleResult(
        created=True,
        event=event,
        warnings=warnings,
        previous_status=previous_status,
        requested_status=status.value,
    )


def validate_paper_order_lifecycle_transition(
    *,
    intent: dict[str, Any] | None,
    requested_status: str,
    previous_status: str | None = None,
    filled_quantity: int | None = None,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    intent_payload = intent if isinstance(intent, dict) else {}
    requested = str(requested_status or "").upper()
    previous = str(previous_status).upper() if previous_status not in (None, "") else None

    if requested not in VALID_PAPER_ORDER_STATES:
        blockers.append("INVALID_PAPER_ORDER_STATUS")
    if not intent_payload:
        blockers.append("PAPER_INTENT_REQUIRED")
    else:
        if intent_payload.get("paper_only") is not True:
            blockers.append("PAPER_INTENT_NOT_PAPER_ONLY")
        if intent_payload.get("is_order_action") is not False:
            blockers.append("PAPER_INTENT_ORDER_FLAG_UNSAFE")
        if intent_payload.get("broker_api_called") is not False:
            blockers.append("PAPER_INTENT_BROKER_API_CALLED")
        if intent_payload.get("real_order_id") not in (None, ""):
            blockers.append("PAPER_INTENT_REAL_ORDER_ID_PRESENT")
        if intent_payload.get("paper_order_intent_id") in (None, ""):
            blockers.append("PAPER_ORDER_INTENT_ID_REQUIRED")
        if intent_payload.get("candidate_id") in (None, ""):
            blockers.append("CANDIDATE_ID_REQUIRED")

    if previous not in VALID_TRANSITIONS:
        blockers.append("UNKNOWN_PREVIOUS_PAPER_ORDER_STATUS")
    elif requested in VALID_PAPER_ORDER_STATES and requested not in VALID_TRANSITIONS[previous]:
        blockers.append("INVALID_PAPER_ORDER_TRANSITION")

    quantity = _int_or_none(intent_payload.get("quantity")) or 0
    requested_fill = _int_or_none(filled_quantity)
    if requested in {"PARTIALLY_FILLED", "FILLED"}:
        if quantity <= 0:
            blockers.append("PAPER_ORDER_QUANTITY_REQUIRED_FOR_FILL")
        if requested_fill is None:
            blockers.append("FILLED_QUANTITY_REQUIRED")
        elif requested_fill <= 0:
            blockers.append("FILLED_QUANTITY_MUST_BE_POSITIVE")
        elif quantity and requested_fill > quantity:
            blockers.append("FILLED_QUANTITY_EXCEEDS_ORDER_QUANTITY")
        elif requested == "PARTIALLY_FILLED" and quantity and requested_fill >= quantity:
            blockers.append("PARTIAL_FILL_MUST_BE_LESS_THAN_ORDER_QUANTITY")
    elif requested_fill not in (None, 0):
        warnings.append("FILLED_QUANTITY_IGNORED_FOR_NON_FILL_STATUS")

    return _dedupe(blockers), _dedupe(warnings)


def _coerce_status(value: str | PaperOrderLifecycleStatus) -> PaperOrderLifecycleStatus | None:
    if isinstance(value, PaperOrderLifecycleStatus):
        return value
    try:
        return PaperOrderLifecycleStatus(str(value).upper())
    except ValueError:
        return None


def _previous_status(previous_event: dict[str, Any] | PaperOrderLifecycleEvent | None) -> str | None:
    if previous_event is None:
        return None
    payload = previous_event.to_dict() if isinstance(previous_event, PaperOrderLifecycleEvent) else previous_event
    if not isinstance(payload, dict):
        return None
    status = payload.get("status")
    return str(status).upper() if status not in (None, "") else None


def _previous_sequence(previous_event: dict[str, Any] | PaperOrderLifecycleEvent | None) -> int:
    if previous_event is None:
        return 0
    payload = previous_event.to_dict() if isinstance(previous_event, PaperOrderLifecycleEvent) else previous_event
    if not isinstance(payload, dict):
        return 0
    return _int_or_none(payload.get("event_sequence")) or 0


def _filled_quantity(
    *,
    status: PaperOrderLifecycleStatus,
    previous_event: dict[str, Any] | PaperOrderLifecycleEvent | None,
    requested_filled_quantity: int | None,
    quantity: int,
) -> int:
    previous_payload = previous_event.to_dict() if isinstance(previous_event, PaperOrderLifecycleEvent) else previous_event
    previous_fill = _int_or_none(previous_payload.get("filled_quantity")) if isinstance(previous_payload, dict) else 0
    if status == PaperOrderLifecycleStatus.FILLED:
        return _int_or_none(requested_filled_quantity) or quantity
    if status == PaperOrderLifecycleStatus.PARTIALLY_FILLED:
        return _int_or_none(requested_filled_quantity) or 0
    return previous_fill or 0


def _stable_paper_order_id(paper_order_intent_id: str, candidate_id: str) -> str:
    seed = "|".join([paper_order_intent_id, candidate_id])
    return f"paper-order-{sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


PAPER_EVENT_SCHEMA_VERSION = "1.0"


class PaperEventType(StrEnum):
    PAPER_ORDER_INTENT_CREATED = "PAPER_ORDER_INTENT_CREATED"
    PAPER_ORDER_ACCEPTED = "PAPER_ORDER_ACCEPTED"
    PAPER_ORDER_REJECTED = "PAPER_ORDER_REJECTED"
    PAPER_ORDER_OPENED = "PAPER_ORDER_OPENED"
    PAPER_ORDER_PARTIALLY_FILLED = "PAPER_ORDER_PARTIALLY_FILLED"
    PAPER_ORDER_FILLED = "PAPER_ORDER_FILLED"
    PAPER_ORDER_CANCELLED = "PAPER_ORDER_CANCELLED"
    PAPER_ORDER_EXPIRED = "PAPER_ORDER_EXPIRED"
    PAPER_POSITION_OPENED = "PAPER_POSITION_OPENED"
    PAPER_POSITION_INCREASED = "PAPER_POSITION_INCREASED"
    PAPER_POSITION_REDUCED = "PAPER_POSITION_REDUCED"
    PAPER_POSITION_CLOSED = "PAPER_POSITION_CLOSED"
    PAPER_POSITION_REVERSED = "PAPER_POSITION_REVERSED"
    PAPER_PNL_MARKED = "PAPER_PNL_MARKED"
    PAPER_SLIPPAGE_MEASURED = "PAPER_SLIPPAGE_MEASURED"
    PAPER_PERFORMANCE_SNAPSHOT_CREATED = "PAPER_PERFORMANCE_SNAPSHOT_CREATED"


VALID_PAPER_EVENT_TYPES = {event_type.value for event_type in PaperEventType}
REQUIRED_PAPER_EVENT_KEYS = [
    "schema_version",
    "event_id",
    "cycle_id",
    "event_sequence",
    "candidate_id",
    "strategy_id",
    "paper_order_intent_id",
    "paper_order_id",
    "event_type",
    "ts_epoch",
    "idempotency_key",
    "payload",
    "paper_only",
    "is_order_action",
    "broker_api_called",
    "real_order_id",
]


@dataclass(frozen=True)
class PaperEvent:
    event_id: str
    cycle_id: str
    event_sequence: int
    candidate_id: str | None
    strategy_id: str | None
    paper_order_intent_id: str | None
    paper_order_id: str | None
    event_type: PaperEventType | str
    ts_epoch: float
    idempotency_key: str
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: str = PAPER_EVENT_SCHEMA_VERSION

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
            "event_id": self.event_id,
            "cycle_id": self.cycle_id,
            "event_sequence": self.event_sequence,
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "paper_order_intent_id": self.paper_order_intent_id,
            "paper_order_id": self.paper_order_id,
            "event_type": _event_type_value(self.event_type),
            "ts_epoch": self.ts_epoch,
            "idempotency_key": self.idempotency_key,
            "payload": dict(self.payload),
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def normalize_paper_event(raw_event: PaperEvent | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw_event, PaperEvent):
        raw = raw_event.to_dict()
    elif isinstance(raw_event, dict):
        raw = dict(raw_event)
    else:
        raise TypeError("paper event must be a PaperEvent or dict")

    normalized = {key: raw.get(key) for key in REQUIRED_PAPER_EVENT_KEYS}
    normalized["schema_version"] = str(normalized.get("schema_version") or PAPER_EVENT_SCHEMA_VERSION)
    normalized["event_id"] = _required_str_or_none(normalized.get("event_id"))
    normalized["cycle_id"] = _required_str_or_none(normalized.get("cycle_id"))
    normalized["candidate_id"] = _optional_str(normalized.get("candidate_id"))
    normalized["strategy_id"] = _optional_str(normalized.get("strategy_id"))
    normalized["paper_order_intent_id"] = _optional_str(normalized.get("paper_order_intent_id"))
    normalized["paper_order_id"] = _optional_str(normalized.get("paper_order_id"))
    normalized["event_type"] = _optional_str(normalized.get("event_type"))
    normalized["idempotency_key"] = _required_str_or_none(normalized.get("idempotency_key"))
    normalized["event_sequence"] = _int_or_none(normalized.get("event_sequence"))
    normalized["ts_epoch"] = _float_or_none(normalized.get("ts_epoch"))
    payload = normalized.get("payload")
    normalized["payload"] = dict(payload) if isinstance(payload, dict) else payload
    normalized["paper_only"] = normalized.get("paper_only")
    normalized["is_order_action"] = normalized.get("is_order_action")
    normalized["broker_api_called"] = normalized.get("broker_api_called")
    normalized["real_order_id"] = normalized.get("real_order_id")
    return normalized


def validate_paper_event(raw_event: PaperEvent | dict[str, Any]) -> list[str]:
    try:
        event = normalize_paper_event(raw_event)
    except (TypeError, ValueError):
        return ["PAPER_EVENT_NOT_OBJECT"]

    blockers: list[str] = []
    for key in REQUIRED_PAPER_EVENT_KEYS:
        if key not in event:
            blockers.append(f"PAPER_EVENT_MISSING_{key.upper()}")

    if event.get("schema_version") != PAPER_EVENT_SCHEMA_VERSION:
        blockers.append("PAPER_EVENT_SCHEMA_VERSION_UNSUPPORTED")
    if not event.get("event_id"):
        blockers.append("PAPER_EVENT_MISSING_EVENT_ID")
    if not event.get("cycle_id"):
        blockers.append("PAPER_EVENT_MISSING_CYCLE_ID")
    if event.get("event_sequence") is None or int(event.get("event_sequence") or 0) < 1:
        blockers.append("PAPER_EVENT_INVALID_EVENT_SEQUENCE")
    if not event.get("event_type"):
        blockers.append("PAPER_EVENT_MISSING_EVENT_TYPE")
    elif event.get("event_type") not in VALID_PAPER_EVENT_TYPES:
        blockers.append("PAPER_EVENT_TYPE_UNSUPPORTED")
    if event.get("ts_epoch") is None:
        blockers.append("PAPER_EVENT_MISSING_TS_EPOCH")
    if not event.get("idempotency_key"):
        blockers.append("PAPER_EVENT_MISSING_IDEMPOTENCY_KEY")
    if not isinstance(event.get("payload"), dict):
        blockers.append("PAPER_EVENT_PAYLOAD_NOT_OBJECT")
    if event.get("paper_only") is not True:
        blockers.append("PAPER_EVENT_UNSAFE_PAPER_ONLY_FLAG")
    if event.get("is_order_action") is not False:
        blockers.append("PAPER_EVENT_UNSAFE_ORDER_ACTION_FLAG")
    if event.get("broker_api_called") is not False:
        blockers.append("PAPER_EVENT_UNSAFE_BROKER_API_FLAG")
    if event.get("real_order_id") is not None:
        blockers.append("PAPER_EVENT_UNSAFE_REAL_ORDER_ID")
    return blockers


def paper_event_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_EVENT_SCHEMA_VERSION,
        "journal_type": "CANONICAL_PAPER_EVENT_JOURNAL",
        "event_types": sorted(VALID_PAPER_EVENT_TYPES),
        "required_event_keys": list(REQUIRED_PAPER_EVENT_KEYS),
        "safe_flags": {
            "paper_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
    }


def _event_type_value(value: PaperEventType | str) -> str:
    return value.value if isinstance(value, PaperEventType) else str(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _required_str_or_none(value: Any) -> str | None:
    return _optional_str(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

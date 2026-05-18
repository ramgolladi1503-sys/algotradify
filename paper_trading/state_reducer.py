from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from paper_trading.events import PAPER_EVENT_SCHEMA_VERSION, normalize_paper_event, validate_paper_event


PAPER_STATE_REDUCER_SCHEMA_VERSION = "1.0"
ORDER_EVENT_STATUS = {
    "PAPER_ORDER_INTENT_CREATED": "INTENT_CREATED",
    "PAPER_ORDER_ACCEPTED": "ACCEPTED",
    "PAPER_ORDER_REJECTED": "REJECTED",
    "PAPER_ORDER_OPENED": "OPEN",
    "PAPER_ORDER_PARTIALLY_FILLED": "PARTIALLY_FILLED",
    "PAPER_ORDER_FILLED": "FILLED",
    "PAPER_ORDER_CANCELLED": "CANCELLED",
    "PAPER_ORDER_EXPIRED": "EXPIRED",
}
POSITION_EVENT_TYPES = {
    "PAPER_POSITION_OPENED",
    "PAPER_POSITION_INCREASED",
    "PAPER_POSITION_REDUCED",
    "PAPER_POSITION_CLOSED",
    "PAPER_POSITION_REVERSED",
}
ANALYTICS_EVENT_BUCKETS = {
    "PAPER_PNL_MARKED": "pnl_marks",
    "PAPER_SLIPPAGE_MEASURED": "slippage_measurements",
    "PAPER_PERFORMANCE_SNAPSHOT_CREATED": "performance_snapshots",
}
TERMINAL_ORDER_STATUSES = {"REJECTED", "FILLED", "CANCELLED", "EXPIRED"}


class PaperStateReducerStatus(StrEnum):
    REDUCED = "REDUCED"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperStateReducerResult:
    reduced: bool
    status: PaperStateReducerStatus
    state: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_STATE_REDUCER_SCHEMA_VERSION

    @property
    def paper_only(self) -> bool:
        return True

    @property
    def read_only(self) -> bool:
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
            "reducer_type": "DETERMINISTIC_PAPER_STATE_REDUCER",
            "reduced": self.reduced,
            "status": self.status.value,
            "state": deepcopy(self.state),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_state_reducer_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_STATE_REDUCER_SCHEMA_VERSION,
        "reducer_type": "DETERMINISTIC_PAPER_STATE_REDUCER",
        "consumes": ["CANONICAL_PAPER_EVENT_JOURNAL"],
        "event_schema_version": PAPER_EVENT_SCHEMA_VERSION,
        "statuses": [status.value for status in PaperStateReducerStatus],
        "order_event_statuses": dict(sorted(ORDER_EVENT_STATUS.items())),
        "position_event_types": sorted(POSITION_EVENT_TYPES),
        "analytics_event_buckets": dict(sorted(ANALYTICS_EVENT_BUCKETS.items())),
        "required_result_keys": [
            "schema_version",
            "reducer_type",
            "reduced",
            "status",
            "state",
            "blockers",
            "warnings",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_state_keys": [
            "schema_version",
            "state_type",
            "orders",
            "positions",
            "pnl_marks",
            "slippage_measurements",
            "performance_snapshots",
            "applied_event_ids",
            "applied_idempotency_keys",
            "last_event",
            "summary",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "safe_flags": {
            "paper_only": True,
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
        "scope_boundary": [
            "pure_reducer_only",
            "no_file_io",
            "no_broker_execution",
            "no_live_orders",
            "no_api",
            "no_ui",
            "no_runtime_wiring",
        ],
    }


def reduce_paper_events(events: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None) -> PaperStateReducerResult:
    blockers, normalized_events = validate_paper_state_reducer_inputs(events)
    if blockers:
        return PaperStateReducerResult(
            reduced=False,
            status=PaperStateReducerStatus.BLOCKED,
            state=_empty_state(),
            blockers=blockers,
        )
    if not normalized_events:
        return PaperStateReducerResult(
            reduced=True,
            status=PaperStateReducerStatus.EMPTY,
            state=_empty_state(),
            warnings=["PAPER_REDUCER_EMPTY_EVENT_LIST"],
        )

    state = _empty_state()
    warnings: list[str] = []
    for event in normalized_events:
        event_type = str(event["event_type"])
        if event_type in ORDER_EVENT_STATUS:
            _apply_order_event(state, event)
        elif event_type in POSITION_EVENT_TYPES:
            _apply_position_event(state, event)
        elif event_type in ANALYTICS_EVENT_BUCKETS:
            _apply_analytics_event(state, event)
        else:
            warnings.append(f"PAPER_REDUCER_EVENT_TYPE_IGNORED:{event_type}")
        state["applied_event_ids"].append(event["event_id"])
        state["applied_idempotency_keys"].append(event["idempotency_key"])
        state["last_event"] = _event_reference(event)

    state["summary"] = _build_summary(state)
    return PaperStateReducerResult(
        reduced=True,
        status=PaperStateReducerStatus.REDUCED,
        state=state,
        warnings=_dedupe(warnings),
    )


def validate_paper_state_reducer_inputs(
    events: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    if events is None:
        return ["PAPER_REDUCER_EVENTS_REQUIRED"], []
    if not isinstance(events, (list, tuple)):
        return ["PAPER_REDUCER_EVENTS_MUST_BE_LIST"], []

    blockers: list[str] = []
    normalized_events: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    seen_idempotency_keys: set[str] = set()
    for index, raw_event in enumerate(events):
        try:
            event = normalize_paper_event(raw_event)
        except (TypeError, ValueError):
            blockers.append(f"EVENT_{index}_PAPER_EVENT_NOT_OBJECT")
            continue
        event_blockers = validate_paper_event(event)
        if event_blockers:
            blockers.extend(f"EVENT_{index}_{blocker}" for blocker in event_blockers)
            continue
        event_id = str(event["event_id"])
        idempotency_key = str(event["idempotency_key"])
        if event_id in seen_event_ids:
            blockers.append(f"EVENT_{index}_PAPER_REDUCER_DUPLICATE_EVENT_ID")
        if idempotency_key in seen_idempotency_keys:
            blockers.append(f"EVENT_{index}_PAPER_REDUCER_DUPLICATE_IDEMPOTENCY_KEY")
        event_type = str(event["event_type"])
        if event_type in POSITION_EVENT_TYPES:
            blockers.extend(_validate_position_event(event, index=index))
        seen_event_ids.add(event_id)
        seen_idempotency_keys.add(idempotency_key)
        normalized_events.append(event)

    return _dedupe(blockers), normalized_events if not blockers else []


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": PAPER_STATE_REDUCER_SCHEMA_VERSION,
        "state_type": "PAPER_REDUCED_STATE",
        "orders": {},
        "positions": {},
        "pnl_marks": [],
        "slippage_measurements": [],
        "performance_snapshots": [],
        "applied_event_ids": [],
        "applied_idempotency_keys": [],
        "last_event": None,
        "summary": {
            "event_count": 0,
            "order_count": 0,
            "open_order_count": 0,
            "terminal_order_count": 0,
            "position_count": 0,
            "open_position_count": 0,
            "flat_position_count": 0,
            "pnl_mark_count": 0,
            "slippage_measurement_count": 0,
            "performance_snapshot_count": 0,
            "paper_only": True,
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _apply_order_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    order_key = _order_key(event)
    existing = dict(state["orders"].get(order_key) or {})
    payload = dict(event.get("payload") or {})
    status = ORDER_EVENT_STATUS[str(event["event_type"])]
    filled_quantity = _first_int(
        payload.get("filled_quantity"),
        payload.get("cumulative_filled_quantity"),
        payload.get("quantity") if status == "FILLED" else None,
        existing.get("filled_quantity"),
    ) or 0
    remaining_quantity = _first_int(payload.get("remaining_quantity"), existing.get("remaining_quantity"))
    average_fill_price = _first_float(payload.get("average_fill_price"), payload.get("fill_price"), existing.get("average_fill_price"))
    order = {
        "paper_order_id": event.get("paper_order_id"),
        "paper_order_intent_id": event.get("paper_order_intent_id"),
        "candidate_id": event.get("candidate_id"),
        "strategy_id": event.get("strategy_id"),
        "status": status,
        "terminal": status in TERMINAL_ORDER_STATUSES,
        "filled_quantity": filled_quantity,
        "remaining_quantity": remaining_quantity,
        "average_fill_price": average_fill_price,
        "last_event_id": event.get("event_id"),
        "last_update_epoch": event.get("ts_epoch"),
        "payload": payload,
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    state["orders"][order_key] = order


def _apply_position_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    payload = dict(event.get("payload") or {})
    position_key = _position_key(event)
    net_quantity = _first_int(payload.get("net_quantity"), 0 if event["event_type"] == "PAPER_POSITION_CLOSED" else None)
    average_entry_price = _first_float(payload.get("average_entry_price"), payload.get("avg_entry_price"))
    position = {
        "position_key": position_key,
        "candidate_id": payload.get("candidate_id", event.get("candidate_id")),
        "strategy_id": payload.get("strategy_id", event.get("strategy_id")),
        "symbol": payload.get("symbol"),
        "tradingsymbol": payload.get("tradingsymbol"),
        "instrument_token": payload.get("instrument_token"),
        "net_quantity": net_quantity,
        "side": _side(net_quantity or 0),
        "average_entry_price": average_entry_price if net_quantity != 0 else None,
        "last_fill_price": _first_float(payload.get("last_fill_price"), payload.get("fill_price")),
        "last_event_type": event.get("event_type"),
        "last_event_id": event.get("event_id"),
        "last_update_epoch": event.get("ts_epoch"),
        "payload": payload,
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    state["positions"][position_key] = position


def _apply_analytics_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    bucket = ANALYTICS_EVENT_BUCKETS[str(event["event_type"])]
    state[bucket].append(
        {
            "event_id": event.get("event_id"),
            "cycle_id": event.get("cycle_id"),
            "candidate_id": event.get("candidate_id"),
            "strategy_id": event.get("strategy_id"),
            "ts_epoch": event.get("ts_epoch"),
            "payload": deepcopy(event.get("payload") or {}),
            "paper_only": True,
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        }
    )


def _build_summary(state: dict[str, Any]) -> dict[str, Any]:
    orders = state["orders"]
    positions = state["positions"]
    terminal_order_count = sum(1 for order in orders.values() if order.get("terminal") is True)
    open_position_count = sum(1 for position in positions.values() if _first_int(position.get("net_quantity"), 0) != 0)
    return {
        "event_count": len(state["applied_event_ids"]),
        "order_count": len(orders),
        "open_order_count": len(orders) - terminal_order_count,
        "terminal_order_count": terminal_order_count,
        "position_count": len(positions),
        "open_position_count": open_position_count,
        "flat_position_count": len(positions) - open_position_count,
        "pnl_mark_count": len(state["pnl_marks"]),
        "slippage_measurement_count": len(state["slippage_measurements"]),
        "performance_snapshot_count": len(state["performance_snapshots"]),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _validate_position_event(event: dict[str, Any], *, index: int) -> list[str]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    blockers: list[str] = []
    if not _position_key(event):
        blockers.append(f"EVENT_{index}_PAPER_REDUCER_POSITION_KEY_REQUIRED")
    if event.get("event_type") != "PAPER_POSITION_CLOSED" and _first_int(payload.get("net_quantity")) is None:
        blockers.append(f"EVENT_{index}_PAPER_REDUCER_POSITION_NET_QUANTITY_REQUIRED")
    return blockers


def _event_reference(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event.get("event_id"),
        "cycle_id": event.get("cycle_id"),
        "event_sequence": event.get("event_sequence"),
        "event_type": event.get("event_type"),
        "ts_epoch": event.get("ts_epoch"),
        "idempotency_key": event.get("idempotency_key"),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _order_key(event: dict[str, Any]) -> str:
    for key in ("paper_order_id", "paper_order_intent_id", "event_id"):
        value = event.get(key)
        if value not in (None, ""):
            return str(value)
    return "UNKNOWN_PAPER_ORDER"


def _position_key(event: dict[str, Any]) -> str | None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    for key in ("position_key", "instrument_token", "tradingsymbol", "symbol"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    for key in ("paper_order_id", "candidate_id"):
        value = event.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _side(net_quantity: int) -> str:
    if net_quantity > 0:
        return "LONG"
    if net_quantity < 0:
        return "SHORT"
    return "FLAT"


def _first_int(*values: Any) -> int | None:
    for value in values:
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_float(*values: Any) -> float | None:
    for value in values:
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
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

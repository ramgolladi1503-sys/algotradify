from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any


PAPER_REALIZED_PNL_SCHEMA_VERSION = "1.0"
FILL_EVENT_STATUSES = {"PARTIALLY_FILLED", "FILLED"}


class PaperRealizedPnlStatus(StrEnum):
    REALIZED = "REALIZED"
    NO_REALIZED_CHANGE = "NO_REALIZED_CHANGE"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperRealizedPnlResult:
    updated: bool
    status: PaperRealizedPnlStatus
    ledger: dict[str, Any] = field(default_factory=dict)
    event: dict[str, Any] | None = None
    realized_quantity: int = 0
    realized_pnl: float = 0.0
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: str = PAPER_REALIZED_PNL_SCHEMA_VERSION

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
            "ledger_type": "PAPER_REALIZED_PNL_LEDGER",
            "updated": self.updated,
            "status": self.status.value,
            "ledger": dict(self.ledger),
            "event": dict(self.event) if self.event else None,
            "realized_quantity": self.realized_quantity,
            "realized_pnl": self.realized_pnl,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_realized_pnl_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_REALIZED_PNL_SCHEMA_VERSION,
        "ledger_type": "PAPER_REALIZED_PNL_LEDGER",
        "consumes": ["PAPER_POSITION_LEDGER", "PAPER_ORDER_INTENT", "PAPER_ORDER_LIFECYCLE_EVENT"],
        "fill_event_statuses": sorted(FILL_EVENT_STATUSES),
        "statuses": [status.value for status in PaperRealizedPnlStatus],
        "required_result_keys": [
            "schema_version",
            "ledger_type",
            "updated",
            "status",
            "ledger",
            "event",
            "realized_quantity",
            "realized_pnl",
            "blockers",
            "warnings",
            "evidence",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_ledger_keys": [
            "schema_version",
            "ledger_type",
            "events",
            "applied_fill_keys",
            "summary",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_event_keys": [
            "realized_event_id",
            "paper_order_id",
            "paper_order_intent_id",
            "candidate_id",
            "position_key",
            "transaction_type",
            "previous_net_quantity",
            "signed_delta_quantity",
            "realized_quantity",
            "average_entry_price",
            "exit_price",
            "realized_pnl",
            "ts_epoch",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_summary_keys": [
            "event_count",
            "winning_event_count",
            "losing_event_count",
            "flat_event_count",
            "total_realized_pnl",
            "total_realized_quantity",
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
        "scope_boundary": [
            "paper_only",
            "realized_pnl_only",
            "no_unrealized_mtm",
            "no_fees",
            "no_slippage_tracker",
            "no_broker_execution",
            "no_live_orders",
            "no_ui",
        ],
    }


def build_paper_realized_pnl(
    *,
    previous_position_ledger: dict[str, Any] | None,
    intent: dict[str, Any] | None,
    lifecycle_event: dict[str, Any] | None,
    previous_realized_ledger: dict[str, Any] | None = None,
    ts_epoch: float | None = None,
) -> PaperRealizedPnlResult:
    blockers, warnings = validate_paper_realized_pnl_inputs(
        previous_position_ledger=previous_position_ledger,
        intent=intent,
        lifecycle_event=lifecycle_event,
        previous_realized_ledger=previous_realized_ledger,
    )
    safe_ledger = _safe_realized_ledger(previous_realized_ledger)
    evidence = _realized_evidence(
        previous_position_ledger=previous_position_ledger,
        intent=intent,
        lifecycle_event=lifecycle_event,
        previous_realized_ledger=previous_realized_ledger,
    )
    if blockers:
        return PaperRealizedPnlResult(
            updated=False,
            status=PaperRealizedPnlStatus.BLOCKED,
            ledger=safe_ledger,
            blockers=blockers,
            warnings=warnings,
            evidence=evidence,
        )

    event_status = str((lifecycle_event or {}).get("status") or "").upper()
    if event_status not in FILL_EVENT_STATUSES:
        return PaperRealizedPnlResult(
            updated=False,
            status=PaperRealizedPnlStatus.NO_REALIZED_CHANGE,
            ledger=safe_ledger,
            warnings=_dedupe(warnings + ["NON_FILL_LIFECYCLE_EVENT_IGNORED"]),
            evidence=evidence,
        )

    intent_payload = dict(intent or {})
    event_payload = dict(lifecycle_event or {})
    previous_ledger = dict(previous_position_ledger or {})
    paper_order_id = str(event_payload.get("paper_order_id"))
    cumulative_filled_quantity = _int_or_none(event_payload.get("filled_quantity")) or 0
    previous_order_filled = _previous_order_fill_quantity(previous_ledger, paper_order_id)
    if cumulative_filled_quantity < previous_order_filled:
        return PaperRealizedPnlResult(
            updated=False,
            status=PaperRealizedPnlStatus.BLOCKED,
            ledger=safe_ledger,
            blockers=["PAPER_FILL_CUMULATIVE_REGRESSION"],
            warnings=warnings,
            evidence=dict(evidence, previous_order_filled_quantity=previous_order_filled),
        )

    delta_quantity = cumulative_filled_quantity - previous_order_filled
    if delta_quantity == 0:
        return PaperRealizedPnlResult(
            updated=False,
            status=PaperRealizedPnlStatus.NO_REALIZED_CHANGE,
            ledger=safe_ledger,
            warnings=_dedupe(warnings + ["DUPLICATE_OR_ALREADY_APPLIED_FILL_EVENT"]),
            evidence=dict(evidence, previous_order_filled_quantity=previous_order_filled),
        )

    fill_key = _fill_key(paper_order_id, cumulative_filled_quantity)
    if fill_key in set(safe_ledger.get("applied_fill_keys") or []):
        return PaperRealizedPnlResult(
            updated=False,
            status=PaperRealizedPnlStatus.NO_REALIZED_CHANGE,
            ledger=safe_ledger,
            warnings=_dedupe(warnings + ["DUPLICATE_REALIZED_PNL_FILL_KEY"]),
            evidence=dict(evidence, fill_key=fill_key),
        )

    position_key = _position_key(intent_payload)
    previous_position = _previous_position(previous_ledger, position_key)
    previous_net = _int_or_none(previous_position.get("net_quantity")) or 0
    signed_delta = delta_quantity if str(intent_payload.get("transaction_type") or "").upper() == "BUY" else -delta_quantity
    realized_quantity = _realized_quantity(previous_net=previous_net, signed_delta=signed_delta)

    if realized_quantity <= 0:
        updated_ledger = _append_fill_key(safe_ledger, fill_key)
        return PaperRealizedPnlResult(
            updated=False,
            status=PaperRealizedPnlStatus.NO_REALIZED_CHANGE,
            ledger=updated_ledger,
            warnings=_dedupe(warnings + ["FILL_DID_NOT_REDUCE_EXISTING_POSITION"]),
            evidence=dict(evidence, fill_key=fill_key, previous_order_filled_quantity=previous_order_filled),
        )

    average_entry_price = _float_or_none(previous_position.get("average_entry_price"))
    exit_price = _float_or_none(event_payload.get("average_fill_price"))
    if average_entry_price is None or exit_price is None:
        return PaperRealizedPnlResult(
            updated=False,
            status=PaperRealizedPnlStatus.BLOCKED,
            ledger=safe_ledger,
            blockers=["REALIZED_PNL_PRICE_INPUT_REQUIRED"],
            warnings=warnings,
            evidence=dict(evidence, fill_key=fill_key, previous_order_filled_quantity=previous_order_filled),
        )

    realized_pnl = _realized_pnl(
        previous_net=previous_net,
        realized_quantity=realized_quantity,
        average_entry_price=average_entry_price,
        exit_price=exit_price,
    )
    realized_event = _realized_event(
        intent=intent_payload,
        lifecycle_event=event_payload,
        position=previous_position,
        fill_key=fill_key,
        previous_net=previous_net,
        signed_delta=signed_delta,
        realized_quantity=realized_quantity,
        average_entry_price=average_entry_price,
        exit_price=exit_price,
        realized_pnl=realized_pnl,
        ts_epoch=ts_epoch if ts_epoch is not None else _float_or_none(event_payload.get("ts_epoch")),
    )
    updated_ledger = _append_realized_event(safe_ledger, realized_event, fill_key)
    return PaperRealizedPnlResult(
        updated=True,
        status=PaperRealizedPnlStatus.REALIZED,
        ledger=updated_ledger,
        event=realized_event,
        realized_quantity=realized_quantity,
        realized_pnl=realized_pnl,
        warnings=warnings,
        evidence=dict(evidence, fill_key=fill_key, previous_order_filled_quantity=previous_order_filled),
    )


def validate_paper_realized_pnl_inputs(
    *,
    previous_position_ledger: dict[str, Any] | None,
    intent: dict[str, Any] | None,
    lifecycle_event: dict[str, Any] | None,
    previous_realized_ledger: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    position_ledger = previous_position_ledger if isinstance(previous_position_ledger, dict) else {}
    intent_payload = intent if isinstance(intent, dict) else {}
    event_payload = lifecycle_event if isinstance(lifecycle_event, dict) else {}
    realized_ledger = previous_realized_ledger if isinstance(previous_realized_ledger, dict) else {}

    if not position_ledger:
        blockers.append("PREVIOUS_PAPER_POSITION_LEDGER_REQUIRED")
    else:
        if position_ledger.get("ledger_type") != "PAPER_POSITION_LEDGER":
            blockers.append("PREVIOUS_PAPER_POSITION_LEDGER_TYPE_REQUIRED")
        _validate_safe_flags(position_ledger, blockers, prefix="PREVIOUS_PAPER_POSITION_LEDGER")
        if not isinstance(position_ledger.get("positions"), dict):
            blockers.append("PREVIOUS_PAPER_POSITION_LEDGER_POSITIONS_INVALID")
        if not isinstance(position_ledger.get("order_fills"), dict):
            blockers.append("PREVIOUS_PAPER_POSITION_LEDGER_ORDER_FILLS_INVALID")

    if not intent_payload:
        blockers.append("PAPER_INTENT_REQUIRED")
    else:
        if intent_payload.get("intent_type") != "PAPER_ORDER_INTENT":
            blockers.append("PAPER_INTENT_TYPE_REQUIRED")
        _validate_safe_flags(intent_payload, blockers, prefix="PAPER_INTENT")
        if str(intent_payload.get("transaction_type") or "").upper() not in {"BUY", "SELL"}:
            blockers.append("PAPER_TRANSACTION_TYPE_REQUIRED")

    if not event_payload:
        blockers.append("PAPER_ORDER_LIFECYCLE_EVENT_REQUIRED")
    else:
        if event_payload.get("event_type") != "PAPER_ORDER_LIFECYCLE_EVENT":
            blockers.append("PAPER_ORDER_LIFECYCLE_EVENT_TYPE_REQUIRED")
        _validate_safe_flags(event_payload, blockers, prefix="PAPER_ORDER_LIFECYCLE")
        if event_payload.get("paper_order_id") in (None, ""):
            blockers.append("PAPER_ORDER_ID_REQUIRED")
        if (_int_or_none(event_payload.get("filled_quantity")) or 0) < 0:
            blockers.append("PAPER_FILLED_QUANTITY_INVALID")

    if intent_payload and event_payload:
        if str(intent_payload.get("paper_order_intent_id")) != str(event_payload.get("paper_order_intent_id")):
            blockers.append("PAPER_INTENT_LIFECYCLE_MISMATCH")
        if str(intent_payload.get("candidate_id")) != str(event_payload.get("candidate_id")):
            blockers.append("PAPER_CANDIDATE_LIFECYCLE_MISMATCH")

    if realized_ledger:
        if realized_ledger.get("ledger_type") != "PAPER_REALIZED_PNL_LEDGER":
            blockers.append("PAPER_REALIZED_PNL_LEDGER_TYPE_REQUIRED")
        _validate_safe_flags(realized_ledger, blockers, prefix="PAPER_REALIZED_PNL_LEDGER")
        if not isinstance(realized_ledger.get("events"), list):
            blockers.append("PAPER_REALIZED_PNL_EVENTS_INVALID")
        if not isinstance(realized_ledger.get("applied_fill_keys"), list):
            blockers.append("PAPER_REALIZED_PNL_APPLIED_KEYS_INVALID")
    elif previous_realized_ledger is None:
        warnings.append("PAPER_REALIZED_PNL_LEDGER_STARTING_EMPTY")

    return _dedupe(blockers), _dedupe(warnings)


def _validate_safe_flags(payload: dict[str, Any], blockers: list[str], *, prefix: str) -> None:
    if payload.get("paper_only") is not True:
        blockers.append(f"{prefix}_NOT_PAPER_ONLY")
    if payload.get("is_order_action") is not False:
        blockers.append(f"{prefix}_ORDER_FLAG_UNSAFE")
    if payload.get("broker_api_called") is not False:
        blockers.append(f"{prefix}_BROKER_API_CALLED")
    if payload.get("real_order_id") not in (None, ""):
        blockers.append(f"{prefix}_REAL_ORDER_ID_PRESENT")


def _safe_realized_ledger(previous_realized_ledger: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(previous_realized_ledger, dict) and previous_realized_ledger.get("ledger_type") == "PAPER_REALIZED_PNL_LEDGER":
        return dict(previous_realized_ledger)
    return _build_realized_ledger(events=[], applied_fill_keys=[])


def _build_realized_ledger(*, events: list[dict[str, Any]], applied_fill_keys: list[str]) -> dict[str, Any]:
    return {
        "schema_version": PAPER_REALIZED_PNL_SCHEMA_VERSION,
        "ledger_type": "PAPER_REALIZED_PNL_LEDGER",
        "events": [dict(event) for event in events],
        "applied_fill_keys": list(applied_fill_keys),
        "summary": _summary(events),
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _append_fill_key(ledger: dict[str, Any], fill_key: str) -> dict[str, Any]:
    events = [dict(event) for event in ledger.get("events") or []]
    keys = list(ledger.get("applied_fill_keys") or [])
    if fill_key not in keys:
        keys.append(fill_key)
    return _build_realized_ledger(events=events, applied_fill_keys=keys)


def _append_realized_event(ledger: dict[str, Any], realized_event: dict[str, Any], fill_key: str) -> dict[str, Any]:
    events = [dict(event) for event in ledger.get("events") or []]
    events.append(dict(realized_event))
    keys = list(ledger.get("applied_fill_keys") or [])
    if fill_key not in keys:
        keys.append(fill_key)
    return _build_realized_ledger(events=events, applied_fill_keys=keys)


def _summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    total = round(sum(_float_or_none(event.get("realized_pnl")) or 0.0 for event in events), 6)
    qty = sum(_int_or_none(event.get("realized_quantity")) or 0 for event in events)
    return {
        "event_count": len(events),
        "winning_event_count": len([event for event in events if (_float_or_none(event.get("realized_pnl")) or 0.0) > 0]),
        "losing_event_count": len([event for event in events if (_float_or_none(event.get("realized_pnl")) or 0.0) < 0]),
        "flat_event_count": len([event for event in events if (_float_or_none(event.get("realized_pnl")) or 0.0) == 0]),
        "total_realized_pnl": total,
        "total_realized_quantity": qty,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _realized_event(
    *,
    intent: dict[str, Any],
    lifecycle_event: dict[str, Any],
    position: dict[str, Any],
    fill_key: str,
    previous_net: int,
    signed_delta: int,
    realized_quantity: int,
    average_entry_price: float,
    exit_price: float,
    realized_pnl: float,
    ts_epoch: float | None,
) -> dict[str, Any]:
    seed = "|".join([fill_key, str(previous_net), str(signed_delta), str(realized_quantity)])
    return {
        "schema_version": PAPER_REALIZED_PNL_SCHEMA_VERSION,
        "event_type": "PAPER_REALIZED_PNL_EVENT",
        "realized_event_id": f"paper-realized-{sha256(seed.encode('utf-8')).hexdigest()[:16]}",
        "fill_key": fill_key,
        "paper_order_id": lifecycle_event.get("paper_order_id"),
        "paper_order_intent_id": lifecycle_event.get("paper_order_intent_id"),
        "candidate_id": lifecycle_event.get("candidate_id"),
        "position_key": position.get("position_key"),
        "symbol": position.get("symbol"),
        "tradingsymbol": position.get("tradingsymbol"),
        "instrument_token": position.get("instrument_token"),
        "strategy": position.get("strategy"),
        "transaction_type": intent.get("transaction_type"),
        "previous_net_quantity": previous_net,
        "signed_delta_quantity": signed_delta,
        "realized_quantity": realized_quantity,
        "average_entry_price": average_entry_price,
        "exit_price": exit_price,
        "realized_pnl": realized_pnl,
        "ts_epoch": ts_epoch,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _realized_quantity(*, previous_net: int, signed_delta: int) -> int:
    if previous_net == 0 or signed_delta == 0:
        return 0
    if previous_net * signed_delta >= 0:
        return 0
    return min(abs(previous_net), abs(signed_delta))


def _realized_pnl(*, previous_net: int, realized_quantity: int, average_entry_price: float, exit_price: float) -> float:
    if previous_net > 0:
        return round((exit_price - average_entry_price) * realized_quantity, 6)
    if previous_net < 0:
        return round((average_entry_price - exit_price) * realized_quantity, 6)
    return 0.0


def _previous_position(ledger: dict[str, Any], position_key: str) -> dict[str, Any]:
    positions = ledger.get("positions") if isinstance(ledger, dict) else {}
    if isinstance(positions, dict) and isinstance(positions.get(position_key), dict):
        return dict(positions[position_key])
    return {}


def _previous_order_fill_quantity(ledger: dict[str, Any], paper_order_id: str) -> int:
    order_fills = ledger.get("order_fills") if isinstance(ledger, dict) else {}
    if not isinstance(order_fills, dict):
        return 0
    return _int_or_none(order_fills.get(paper_order_id)) or 0


def _position_key(intent: dict[str, Any]) -> str:
    for key in ("instrument_token", "tradingsymbol", "symbol", "candidate_id"):
        value = intent.get(key)
        if value not in (None, ""):
            return str(value)
    return "UNKNOWN_PAPER_POSITION"


def _fill_key(paper_order_id: str, cumulative_filled_quantity: int) -> str:
    return f"{paper_order_id}:{cumulative_filled_quantity}"


def _realized_evidence(
    *,
    previous_position_ledger: dict[str, Any] | None,
    intent: dict[str, Any] | None,
    lifecycle_event: dict[str, Any] | None,
    previous_realized_ledger: dict[str, Any] | None,
) -> dict[str, Any]:
    position_ledger = previous_position_ledger if isinstance(previous_position_ledger, dict) else {}
    intent_payload = intent if isinstance(intent, dict) else {}
    event_payload = lifecycle_event if isinstance(lifecycle_event, dict) else {}
    realized_ledger = previous_realized_ledger if isinstance(previous_realized_ledger, dict) else {}
    return {
        "previous_position_ledger_type": position_ledger.get("ledger_type"),
        "previous_position_count": len(position_ledger.get("positions") or {}) if isinstance(position_ledger.get("positions"), dict) else 0,
        "previous_realized_event_count": len(realized_ledger.get("events") or []) if isinstance(realized_ledger.get("events"), list) else 0,
        "paper_order_intent_id": intent_payload.get("paper_order_intent_id"),
        "paper_order_id": event_payload.get("paper_order_id"),
        "candidate_id": intent_payload.get("candidate_id"),
        "event_status": event_payload.get("status"),
        "event_filled_quantity": event_payload.get("filled_quantity"),
        "realized_pnl_only": True,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


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

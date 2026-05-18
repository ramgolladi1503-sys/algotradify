from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any


PAPER_POSITION_LEDGER_SCHEMA_VERSION = "1.0"
POSITION_FILL_STATUSES = {"PARTIALLY_FILLED", "FILLED"}


class PaperPositionLedgerStatus(StrEnum):
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_INCREASED = "POSITION_INCREASED"
    POSITION_REDUCED = "POSITION_REDUCED"
    POSITION_CLOSED = "POSITION_CLOSED"
    POSITION_REVERSED = "POSITION_REVERSED"
    NO_POSITION_CHANGE = "NO_POSITION_CHANGE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperPositionLedgerResult:
    updated: bool
    status: PaperPositionLedgerStatus
    ledger: dict[str, Any] = field(default_factory=dict)
    position: dict[str, Any] | None = None
    delta_quantity: int = 0
    signed_delta_quantity: int = 0
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: str = PAPER_POSITION_LEDGER_SCHEMA_VERSION

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
            "ledger_type": "PAPER_POSITION_LEDGER",
            "updated": self.updated,
            "status": self.status.value,
            "ledger": dict(self.ledger),
            "position": dict(self.position) if self.position else None,
            "delta_quantity": self.delta_quantity,
            "signed_delta_quantity": self.signed_delta_quantity,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_position_ledger_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_POSITION_LEDGER_SCHEMA_VERSION,
        "ledger_type": "PAPER_POSITION_LEDGER",
        "consumes": ["PAPER_ORDER_INTENT", "PAPER_ORDER_LIFECYCLE_EVENT"],
        "fill_event_statuses": sorted(POSITION_FILL_STATUSES),
        "statuses": [status.value for status in PaperPositionLedgerStatus],
        "required_result_keys": [
            "schema_version",
            "ledger_type",
            "updated",
            "status",
            "ledger",
            "position",
            "delta_quantity",
            "signed_delta_quantity",
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
            "positions",
            "order_fills",
            "last_event",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_position_keys": [
            "position_id",
            "position_key",
            "candidate_id",
            "symbol",
            "tradingsymbol",
            "instrument_token",
            "strategy",
            "net_quantity",
            "side",
            "average_entry_price",
            "last_fill_price",
            "last_update_epoch",
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
            "fill_events_only",
            "no_broker_execution",
            "no_live_orders",
            "no_pnl",
            "no_slippage_tracker",
            "no_ui",
        ],
    }


def build_paper_position_ledger(
    *,
    intent: dict[str, Any] | None,
    lifecycle_event: dict[str, Any] | None,
    previous_ledger: dict[str, Any] | None = None,
    ts_epoch: float | None = None,
) -> PaperPositionLedgerResult:
    blockers, warnings = validate_paper_position_ledger_inputs(
        intent=intent,
        lifecycle_event=lifecycle_event,
        previous_ledger=previous_ledger,
    )
    evidence = _ledger_evidence(intent=intent, lifecycle_event=lifecycle_event, previous_ledger=previous_ledger)
    safe_previous = _safe_ledger(previous_ledger)

    if blockers:
        return PaperPositionLedgerResult(
            updated=False,
            status=PaperPositionLedgerStatus.BLOCKED,
            ledger=safe_previous,
            blockers=blockers,
            warnings=warnings,
            evidence=evidence,
        )

    intent_payload = dict(intent or {})
    event_payload = dict(lifecycle_event or {})
    event_status = str(event_payload.get("status") or "").upper()
    if event_status not in POSITION_FILL_STATUSES:
        return PaperPositionLedgerResult(
            updated=False,
            status=PaperPositionLedgerStatus.NO_POSITION_CHANGE,
            ledger=safe_previous,
            warnings=_dedupe(warnings + ["NON_FILL_LIFECYCLE_EVENT_IGNORED"]),
            evidence=evidence,
        )

    paper_order_id = str(event_payload.get("paper_order_id"))
    cumulative_filled_quantity = _int_or_none(event_payload.get("filled_quantity")) or 0
    previous_order_filled = _previous_order_fill_quantity(safe_previous, paper_order_id)
    if cumulative_filled_quantity < previous_order_filled:
        return PaperPositionLedgerResult(
            updated=False,
            status=PaperPositionLedgerStatus.BLOCKED,
            ledger=safe_previous,
            blockers=["PAPER_FILL_CUMULATIVE_REGRESSION"],
            warnings=warnings,
            evidence=dict(evidence, previous_order_filled_quantity=previous_order_filled),
        )

    delta_quantity = cumulative_filled_quantity - previous_order_filled
    if delta_quantity == 0:
        return PaperPositionLedgerResult(
            updated=False,
            status=PaperPositionLedgerStatus.NO_POSITION_CHANGE,
            ledger=safe_previous,
            warnings=_dedupe(warnings + ["DUPLICATE_OR_ALREADY_APPLIED_FILL_EVENT"]),
            evidence=dict(evidence, previous_order_filled_quantity=previous_order_filled),
        )

    transaction_type = str(intent_payload.get("transaction_type") or "").upper()
    signed_delta = delta_quantity if transaction_type == "BUY" else -delta_quantity
    position_key = _position_key(intent_payload)
    positions = dict(safe_previous.get("positions") or {})
    previous_position = dict(positions.get(position_key) or _empty_position(intent_payload, position_key))
    position = _apply_position_delta(
        previous_position=previous_position,
        signed_delta=signed_delta,
        fill_price=_float_or_none(event_payload.get("average_fill_price")),
        ts_epoch=ts_epoch if ts_epoch is not None else _float_or_none(event_payload.get("ts_epoch")),
    )
    positions[position_key] = position

    order_fills = dict(safe_previous.get("order_fills") or {})
    order_fills[paper_order_id] = cumulative_filled_quantity
    ledger = _build_ledger(
        positions=positions,
        order_fills=order_fills,
        last_event=event_payload,
    )

    return PaperPositionLedgerResult(
        updated=True,
        status=_position_status(previous_net=_int_or_none(previous_position.get("net_quantity")) or 0, new_net=position["net_quantity"], signed_delta=signed_delta),
        ledger=ledger,
        position=position,
        delta_quantity=delta_quantity,
        signed_delta_quantity=signed_delta,
        warnings=warnings,
        evidence=dict(evidence, previous_order_filled_quantity=previous_order_filled),
    )


def validate_paper_position_ledger_inputs(
    *,
    intent: dict[str, Any] | None,
    lifecycle_event: dict[str, Any] | None,
    previous_ledger: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    intent_payload = intent if isinstance(intent, dict) else {}
    event_payload = lifecycle_event if isinstance(lifecycle_event, dict) else {}
    ledger_payload = previous_ledger if isinstance(previous_ledger, dict) else {}

    if not intent_payload:
        blockers.append("PAPER_INTENT_REQUIRED")
    else:
        if intent_payload.get("intent_type") != "PAPER_ORDER_INTENT":
            blockers.append("PAPER_INTENT_TYPE_REQUIRED")
        _validate_safe_flags(intent_payload, blockers, prefix="PAPER_INTENT")
        if (_int_or_none(intent_payload.get("quantity")) or 0) <= 0:
            blockers.append("PAPER_ORDER_QUANTITY_REQUIRED")
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

    if ledger_payload:
        if ledger_payload.get("ledger_type") != "PAPER_POSITION_LEDGER":
            blockers.append("PAPER_POSITION_LEDGER_TYPE_REQUIRED")
        _validate_safe_flags(ledger_payload, blockers, prefix="PAPER_POSITION_LEDGER")
        positions = ledger_payload.get("positions")
        order_fills = ledger_payload.get("order_fills")
        if not isinstance(positions, dict):
            blockers.append("PAPER_POSITION_LEDGER_POSITIONS_INVALID")
        if not isinstance(order_fills, dict):
            blockers.append("PAPER_POSITION_LEDGER_ORDER_FILLS_INVALID")
    elif previous_ledger is None:
        warnings.append("PAPER_POSITION_LEDGER_STARTING_EMPTY")

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


def _safe_ledger(previous_ledger: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(previous_ledger, dict) and previous_ledger.get("ledger_type") == "PAPER_POSITION_LEDGER":
        return dict(previous_ledger)
    return _build_ledger(positions={}, order_fills={}, last_event=None)


def _build_ledger(*, positions: dict[str, Any], order_fills: dict[str, int], last_event: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "schema_version": PAPER_POSITION_LEDGER_SCHEMA_VERSION,
        "ledger_type": "PAPER_POSITION_LEDGER",
        "positions": dict(positions),
        "order_fills": dict(order_fills),
        "last_event": dict(last_event) if isinstance(last_event, dict) else None,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _empty_position(intent: dict[str, Any], position_key: str) -> dict[str, Any]:
    return {
        "position_id": _stable_position_id(position_key),
        "position_key": position_key,
        "candidate_id": intent.get("candidate_id"),
        "symbol": intent.get("symbol"),
        "tradingsymbol": intent.get("tradingsymbol"),
        "instrument_token": intent.get("instrument_token"),
        "strategy": intent.get("strategy"),
        "net_quantity": 0,
        "side": "FLAT",
        "average_entry_price": None,
        "last_fill_price": None,
        "last_update_epoch": None,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _apply_position_delta(
    *,
    previous_position: dict[str, Any],
    signed_delta: int,
    fill_price: float | None,
    ts_epoch: float | None,
) -> dict[str, Any]:
    previous_net = _int_or_none(previous_position.get("net_quantity")) or 0
    previous_avg = _float_or_none(previous_position.get("average_entry_price"))
    new_net = previous_net + signed_delta
    new_avg = _next_average_price(previous_net=previous_net, previous_avg=previous_avg, signed_delta=signed_delta, fill_price=fill_price)
    position = dict(previous_position)
    position.update(
        {
            "net_quantity": new_net,
            "side": _side(new_net),
            "average_entry_price": new_avg,
            "last_fill_price": fill_price,
            "last_update_epoch": ts_epoch,
            "paper_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        }
    )
    return position


def _next_average_price(*, previous_net: int, previous_avg: float | None, signed_delta: int, fill_price: float | None) -> float | None:
    new_net = previous_net + signed_delta
    if new_net == 0:
        return None
    if fill_price is None:
        return previous_avg
    if previous_net == 0 or previous_net * signed_delta < 0 and abs(signed_delta) > abs(previous_net):
        return fill_price
    if previous_net * signed_delta > 0:
        previous_abs = abs(previous_net)
        delta_abs = abs(signed_delta)
        if previous_avg is None:
            return fill_price
        return round(((previous_avg * previous_abs) + (fill_price * delta_abs)) / (previous_abs + delta_abs), 6)
    return previous_avg


def _position_status(*, previous_net: int, new_net: int, signed_delta: int) -> PaperPositionLedgerStatus:
    if previous_net == 0 and new_net != 0:
        return PaperPositionLedgerStatus.POSITION_OPENED
    if new_net == 0:
        return PaperPositionLedgerStatus.POSITION_CLOSED
    if previous_net * new_net < 0:
        return PaperPositionLedgerStatus.POSITION_REVERSED
    if abs(new_net) > abs(previous_net):
        return PaperPositionLedgerStatus.POSITION_INCREASED
    if signed_delta != 0 and abs(new_net) < abs(previous_net):
        return PaperPositionLedgerStatus.POSITION_REDUCED
    return PaperPositionLedgerStatus.NO_POSITION_CHANGE


def _position_key(intent: dict[str, Any]) -> str:
    for key in ("instrument_token", "tradingsymbol", "symbol", "candidate_id"):
        value = intent.get(key)
        if value not in (None, ""):
            return str(value)
    return "UNKNOWN_PAPER_POSITION"


def _previous_order_fill_quantity(ledger: dict[str, Any], paper_order_id: str) -> int:
    order_fills = ledger.get("order_fills") if isinstance(ledger, dict) else {}
    if not isinstance(order_fills, dict):
        return 0
    return _int_or_none(order_fills.get(paper_order_id)) or 0


def _ledger_evidence(
    *,
    intent: dict[str, Any] | None,
    lifecycle_event: dict[str, Any] | None,
    previous_ledger: dict[str, Any] | None,
) -> dict[str, Any]:
    intent_payload = intent if isinstance(intent, dict) else {}
    event_payload = lifecycle_event if isinstance(lifecycle_event, dict) else {}
    ledger_payload = previous_ledger if isinstance(previous_ledger, dict) else {}
    return {
        "paper_order_intent_id": intent_payload.get("paper_order_intent_id"),
        "paper_order_id": event_payload.get("paper_order_id"),
        "candidate_id": intent_payload.get("candidate_id"),
        "event_status": event_payload.get("status"),
        "event_filled_quantity": event_payload.get("filled_quantity"),
        "previous_position_count": len(ledger_payload.get("positions") or {}) if isinstance(ledger_payload.get("positions"), dict) else 0,
        "previous_order_fill_count": len(ledger_payload.get("order_fills") or {}) if isinstance(ledger_payload.get("order_fills"), dict) else 0,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _stable_position_id(position_key: str) -> str:
    return f"paper-position-{sha256(position_key.encode('utf-8')).hexdigest()[:16]}"


def _side(net_quantity: int) -> str:
    if net_quantity > 0:
        return "LONG"
    if net_quantity < 0:
        return "SHORT"
    return "FLAT"


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

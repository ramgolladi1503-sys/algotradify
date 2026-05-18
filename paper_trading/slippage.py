from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any


PAPER_SLIPPAGE_SCHEMA_VERSION = "1.0"
FILL_EVENT_STATUSES = {"PARTIALLY_FILLED", "FILLED"}


class PaperSlippageStatus(StrEnum):
    MEASURED = "MEASURED"
    NO_FILL = "NO_FILL"
    NO_SLIPPAGE_CHANGE = "NO_SLIPPAGE_CHANGE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperSlippageResult:
    measured: bool
    status: PaperSlippageStatus
    report: dict[str, Any] = field(default_factory=dict)
    event: dict[str, Any] | None = None
    measured_quantity: int = 0
    slippage_per_unit: float = 0.0
    slippage_amount: float = 0.0
    slippage_bps: float | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: str = PAPER_SLIPPAGE_SCHEMA_VERSION

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
            "report_type": "PAPER_SLIPPAGE_FILL_QUALITY",
            "measured": self.measured,
            "status": self.status.value,
            "report": dict(self.report),
            "event": dict(self.event) if self.event else None,
            "measured_quantity": self.measured_quantity,
            "slippage_per_unit": self.slippage_per_unit,
            "slippage_amount": self.slippage_amount,
            "slippage_bps": self.slippage_bps,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_slippage_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_SLIPPAGE_SCHEMA_VERSION,
        "report_type": "PAPER_SLIPPAGE_FILL_QUALITY",
        "consumes": ["PAPER_ORDER_INTENT", "PAPER_ORDER_LIFECYCLE_EVENT", "CONTROLLED_EXPECTED_PRICE"],
        "fill_event_statuses": sorted(FILL_EVENT_STATUSES),
        "statuses": [status.value for status in PaperSlippageStatus],
        "required_result_keys": [
            "schema_version",
            "report_type",
            "measured",
            "status",
            "report",
            "event",
            "measured_quantity",
            "slippage_per_unit",
            "slippage_amount",
            "slippage_bps",
            "blockers",
            "warnings",
            "evidence",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_report_keys": [
            "schema_version",
            "report_type",
            "events",
            "applied_fill_keys",
            "order_fills",
            "summary",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_event_keys": [
            "slippage_event_id",
            "fill_key",
            "paper_order_id",
            "paper_order_intent_id",
            "candidate_id",
            "transaction_type",
            "expected_price",
            "fill_price",
            "measured_quantity",
            "slippage_per_unit",
            "slippage_amount",
            "slippage_bps",
            "slippage_quality",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_summary_keys": [
            "event_count",
            "measured_quantity",
            "total_slippage_amount",
            "average_slippage_per_unit",
            "weighted_average_slippage_bps",
            "favorable_event_count",
            "unfavorable_event_count",
            "flat_event_count",
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
            "fill_quality_evidence_only",
            "no_broker_execution",
            "no_live_orders",
            "no_pnl_mutation",
            "no_fees",
            "no_ui",
        ],
    }


def build_paper_slippage_report(
    *,
    intent: dict[str, Any] | None,
    lifecycle_event: dict[str, Any] | None,
    expected_price: float | int | str | None = None,
    previous_report: dict[str, Any] | None = None,
    ts_epoch: float | None = None,
) -> PaperSlippageResult:
    blockers, warnings = validate_paper_slippage_inputs(
        intent=intent,
        lifecycle_event=lifecycle_event,
        expected_price=expected_price,
        previous_report=previous_report,
    )
    safe_report = _safe_report(previous_report)
    evidence = _slippage_evidence(intent=intent, lifecycle_event=lifecycle_event, expected_price=expected_price, previous_report=previous_report)
    if blockers:
        return PaperSlippageResult(
            measured=False,
            status=PaperSlippageStatus.BLOCKED,
            report=safe_report,
            blockers=blockers,
            warnings=warnings,
            evidence=evidence,
        )

    intent_payload = dict(intent or {})
    event_payload = dict(lifecycle_event or {})
    event_status = str(event_payload.get("status") or "").upper()
    if event_status not in FILL_EVENT_STATUSES:
        return PaperSlippageResult(
            measured=False,
            status=PaperSlippageStatus.NO_FILL,
            report=safe_report,
            warnings=_dedupe(warnings + ["NON_FILL_LIFECYCLE_EVENT_IGNORED"]),
            evidence=evidence,
        )

    paper_order_id = str(event_payload.get("paper_order_id"))
    cumulative_filled_quantity = _int_or_none(event_payload.get("filled_quantity")) or 0
    previous_order_filled = _previous_order_fill_quantity(safe_report, paper_order_id)
    if cumulative_filled_quantity < previous_order_filled:
        return PaperSlippageResult(
            measured=False,
            status=PaperSlippageStatus.BLOCKED,
            report=safe_report,
            blockers=["PAPER_FILL_CUMULATIVE_REGRESSION"],
            warnings=warnings,
            evidence=dict(evidence, previous_order_filled_quantity=previous_order_filled),
        )

    measured_quantity = cumulative_filled_quantity - previous_order_filled
    fill_key = _fill_key(paper_order_id, cumulative_filled_quantity)
    if fill_key in set(safe_report.get("applied_fill_keys") or []):
        return PaperSlippageResult(
            measured=False,
            status=PaperSlippageStatus.NO_SLIPPAGE_CHANGE,
            report=safe_report,
            warnings=_dedupe(warnings + ["DUPLICATE_SLIPPAGE_FILL_KEY"]),
            evidence=dict(evidence, fill_key=fill_key),
        )
    if measured_quantity <= 0:
        updated_report = _append_fill_key(safe_report, fill_key=fill_key, paper_order_id=paper_order_id, cumulative_filled_quantity=cumulative_filled_quantity)
        return PaperSlippageResult(
            measured=False,
            status=PaperSlippageStatus.NO_SLIPPAGE_CHANGE,
            report=updated_report,
            warnings=_dedupe(warnings + ["DUPLICATE_OR_ALREADY_APPLIED_FILL_EVENT"]),
            evidence=dict(evidence, fill_key=fill_key, previous_order_filled_quantity=previous_order_filled),
        )

    resolved_expected_price = _resolved_expected_price(intent_payload, expected_price)
    fill_price = _float_or_none(event_payload.get("average_fill_price"))
    if resolved_expected_price is None or fill_price is None:
        return PaperSlippageResult(
            measured=False,
            status=PaperSlippageStatus.BLOCKED,
            report=safe_report,
            blockers=["SLIPPAGE_PRICE_INPUT_REQUIRED"],
            warnings=warnings,
            evidence=dict(evidence, fill_key=fill_key, previous_order_filled_quantity=previous_order_filled),
        )

    transaction_type = str(intent_payload.get("transaction_type") or "").upper()
    slippage_per_unit = _slippage_per_unit(transaction_type=transaction_type, expected_price=resolved_expected_price, fill_price=fill_price)
    slippage_amount = round(slippage_per_unit * measured_quantity, 6)
    slippage_bps = round((slippage_per_unit / resolved_expected_price) * 10000, 6) if resolved_expected_price else None
    slippage_event = _slippage_event(
        intent=intent_payload,
        lifecycle_event=event_payload,
        fill_key=fill_key,
        expected_price=resolved_expected_price,
        fill_price=fill_price,
        measured_quantity=measured_quantity,
        slippage_per_unit=slippage_per_unit,
        slippage_amount=slippage_amount,
        slippage_bps=slippage_bps,
        ts_epoch=ts_epoch if ts_epoch is not None else _float_or_none(event_payload.get("ts_epoch")),
    )
    updated_report = _append_slippage_event(safe_report, slippage_event, fill_key, paper_order_id, cumulative_filled_quantity)
    return PaperSlippageResult(
        measured=True,
        status=PaperSlippageStatus.MEASURED,
        report=updated_report,
        event=slippage_event,
        measured_quantity=measured_quantity,
        slippage_per_unit=slippage_per_unit,
        slippage_amount=slippage_amount,
        slippage_bps=slippage_bps,
        warnings=warnings,
        evidence=dict(evidence, fill_key=fill_key, previous_order_filled_quantity=previous_order_filled),
    )


def validate_paper_slippage_inputs(
    *,
    intent: dict[str, Any] | None,
    lifecycle_event: dict[str, Any] | None,
    expected_price: float | int | str | None = None,
    previous_report: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    intent_payload = intent if isinstance(intent, dict) else {}
    event_payload = lifecycle_event if isinstance(lifecycle_event, dict) else {}
    report_payload = previous_report if isinstance(previous_report, dict) else {}

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

    if _resolved_expected_price(intent_payload, expected_price) is None:
        blockers.append("CONTROLLED_EXPECTED_PRICE_REQUIRED")

    if report_payload:
        if report_payload.get("report_type") != "PAPER_SLIPPAGE_FILL_QUALITY":
            blockers.append("PAPER_SLIPPAGE_REPORT_TYPE_REQUIRED")
        _validate_safe_flags(report_payload, blockers, prefix="PAPER_SLIPPAGE_REPORT")
        if not isinstance(report_payload.get("events"), list):
            blockers.append("PAPER_SLIPPAGE_EVENTS_INVALID")
        if not isinstance(report_payload.get("applied_fill_keys"), list):
            blockers.append("PAPER_SLIPPAGE_APPLIED_KEYS_INVALID")
        if not isinstance(report_payload.get("order_fills"), dict):
            blockers.append("PAPER_SLIPPAGE_ORDER_FILLS_INVALID")
    elif previous_report is None:
        warnings.append("PAPER_SLIPPAGE_REPORT_STARTING_EMPTY")

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


def _safe_report(previous_report: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(previous_report, dict) and previous_report.get("report_type") == "PAPER_SLIPPAGE_FILL_QUALITY":
        return dict(previous_report)
    return _build_report(events=[], applied_fill_keys=[], order_fills={})


def _build_report(*, events: list[dict[str, Any]], applied_fill_keys: list[str], order_fills: dict[str, int]) -> dict[str, Any]:
    return {
        "schema_version": PAPER_SLIPPAGE_SCHEMA_VERSION,
        "report_type": "PAPER_SLIPPAGE_FILL_QUALITY",
        "events": [dict(event) for event in events],
        "applied_fill_keys": list(applied_fill_keys),
        "order_fills": dict(order_fills),
        "summary": _summary(events),
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _append_fill_key(report: dict[str, Any], *, fill_key: str, paper_order_id: str, cumulative_filled_quantity: int) -> dict[str, Any]:
    events = [dict(event) for event in report.get("events") or []]
    keys = list(report.get("applied_fill_keys") or [])
    order_fills = dict(report.get("order_fills") or {})
    if fill_key not in keys:
        keys.append(fill_key)
    order_fills[paper_order_id] = cumulative_filled_quantity
    return _build_report(events=events, applied_fill_keys=keys, order_fills=order_fills)


def _append_slippage_event(
    report: dict[str, Any],
    slippage_event: dict[str, Any],
    fill_key: str,
    paper_order_id: str,
    cumulative_filled_quantity: int,
) -> dict[str, Any]:
    events = [dict(event) for event in report.get("events") or []]
    events.append(dict(slippage_event))
    keys = list(report.get("applied_fill_keys") or [])
    if fill_key not in keys:
        keys.append(fill_key)
    order_fills = dict(report.get("order_fills") or {})
    order_fills[paper_order_id] = cumulative_filled_quantity
    return _build_report(events=events, applied_fill_keys=keys, order_fills=order_fills)


def _summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    measured_quantity = sum(_int_or_none(event.get("measured_quantity")) or 0 for event in events)
    total_amount = round(sum(_float_or_none(event.get("slippage_amount")) or 0.0 for event in events), 6)
    avg_per_unit = round(total_amount / measured_quantity, 6) if measured_quantity else 0.0
    weighted_bps = _weighted_average_bps(events, measured_quantity)
    return {
        "event_count": len(events),
        "measured_quantity": measured_quantity,
        "total_slippage_amount": total_amount,
        "average_slippage_per_unit": avg_per_unit,
        "weighted_average_slippage_bps": weighted_bps,
        "favorable_event_count": len([event for event in events if (_float_or_none(event.get("slippage_amount")) or 0.0) < 0]),
        "unfavorable_event_count": len([event for event in events if (_float_or_none(event.get("slippage_amount")) or 0.0) > 0]),
        "flat_event_count": len([event for event in events if (_float_or_none(event.get("slippage_amount")) or 0.0) == 0]),
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _weighted_average_bps(events: list[dict[str, Any]], measured_quantity: int) -> float | None:
    if not measured_quantity:
        return 0.0
    numerator = 0.0
    for event in events:
        bps = _float_or_none(event.get("slippage_bps"))
        qty = _int_or_none(event.get("measured_quantity")) or 0
        if bps is not None:
            numerator += bps * qty
    return round(numerator / measured_quantity, 6)


def _slippage_event(
    *,
    intent: dict[str, Any],
    lifecycle_event: dict[str, Any],
    fill_key: str,
    expected_price: float,
    fill_price: float,
    measured_quantity: int,
    slippage_per_unit: float,
    slippage_amount: float,
    slippage_bps: float | None,
    ts_epoch: float | None,
) -> dict[str, Any]:
    seed = "|".join([fill_key, str(expected_price), str(fill_price), str(measured_quantity)])
    return {
        "schema_version": PAPER_SLIPPAGE_SCHEMA_VERSION,
        "event_type": "PAPER_SLIPPAGE_FILL_QUALITY_EVENT",
        "slippage_event_id": f"paper-slippage-{sha256(seed.encode('utf-8')).hexdigest()[:16]}",
        "fill_key": fill_key,
        "paper_order_id": lifecycle_event.get("paper_order_id"),
        "paper_order_intent_id": lifecycle_event.get("paper_order_intent_id"),
        "candidate_id": lifecycle_event.get("candidate_id"),
        "symbol": intent.get("symbol"),
        "tradingsymbol": intent.get("tradingsymbol"),
        "instrument_token": intent.get("instrument_token"),
        "strategy": intent.get("strategy"),
        "transaction_type": intent.get("transaction_type"),
        "expected_price": expected_price,
        "fill_price": fill_price,
        "measured_quantity": measured_quantity,
        "slippage_per_unit": slippage_per_unit,
        "slippage_amount": slippage_amount,
        "slippage_bps": slippage_bps,
        "slippage_quality": _quality(slippage_amount),
        "ts_epoch": ts_epoch,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _slippage_per_unit(*, transaction_type: str, expected_price: float, fill_price: float) -> float:
    if transaction_type == "BUY":
        return round(fill_price - expected_price, 6)
    if transaction_type == "SELL":
        return round(expected_price - fill_price, 6)
    return 0.0


def _quality(slippage_amount: float) -> str:
    if slippage_amount > 0:
        return "UNFAVORABLE"
    if slippage_amount < 0:
        return "FAVORABLE"
    return "FLAT"


def _resolved_expected_price(intent: dict[str, Any], expected_price: float | int | str | None) -> float | None:
    explicit = _float_or_none(expected_price)
    if explicit is not None:
        return explicit
    for key in ("expected_price", "reference_price", "price", "entry_price", "entry"):
        value = _float_or_none(intent.get(key))
        if value is not None:
            return value
    return None


def _previous_order_fill_quantity(report: dict[str, Any], paper_order_id: str) -> int:
    order_fills = report.get("order_fills") if isinstance(report, dict) else {}
    if not isinstance(order_fills, dict):
        return 0
    return _int_or_none(order_fills.get(paper_order_id)) or 0


def _fill_key(paper_order_id: str, cumulative_filled_quantity: int) -> str:
    return f"{paper_order_id}:{cumulative_filled_quantity}"


def _slippage_evidence(
    *,
    intent: dict[str, Any] | None,
    lifecycle_event: dict[str, Any] | None,
    expected_price: float | int | str | None,
    previous_report: dict[str, Any] | None,
) -> dict[str, Any]:
    intent_payload = intent if isinstance(intent, dict) else {}
    event_payload = lifecycle_event if isinstance(lifecycle_event, dict) else {}
    report_payload = previous_report if isinstance(previous_report, dict) else {}
    return {
        "paper_order_intent_id": intent_payload.get("paper_order_intent_id"),
        "paper_order_id": event_payload.get("paper_order_id"),
        "candidate_id": intent_payload.get("candidate_id"),
        "event_status": event_payload.get("status"),
        "event_filled_quantity": event_payload.get("filled_quantity"),
        "expected_price": _resolved_expected_price(intent_payload, expected_price),
        "previous_slippage_event_count": len(report_payload.get("events") or []) if isinstance(report_payload.get("events"), list) else 0,
        "fill_quality_evidence_only": True,
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

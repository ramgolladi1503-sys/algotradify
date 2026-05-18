from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


PAPER_MTM_PNL_SCHEMA_VERSION = "1.0"
CONTROLLED_MARK_SOURCES = {"CONTROLLED_MARK", "TEST_MARK", "SIMULATED_MARK", "PAPER_MARK"}
OPEN_POSITION_SIDES = {"LONG", "SHORT"}


class PaperMtmPnlStatus(StrEnum):
    VALUED = "VALUED"
    DEGRADED_MISSING_MARK = "DEGRADED_MISSING_MARK"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperMtmPnlResult:
    valued: bool
    status: PaperMtmPnlStatus
    rows: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: str = PAPER_MTM_PNL_SCHEMA_VERSION

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
            "tracker_type": "PAPER_MTM_PNL_TRACKER",
            "valued": self.valued,
            "status": self.status.value,
            "rows": [dict(row) for row in self.rows],
            "summary": dict(self.summary),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_mtm_pnl_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_MTM_PNL_SCHEMA_VERSION,
        "tracker_type": "PAPER_MTM_PNL_TRACKER",
        "consumes": ["PAPER_POSITION_LEDGER", "CONTROLLED_MARK"],
        "statuses": [status.value for status in PaperMtmPnlStatus],
        "controlled_mark_sources": sorted(CONTROLLED_MARK_SOURCES),
        "required_result_keys": [
            "schema_version",
            "tracker_type",
            "valued",
            "status",
            "rows",
            "summary",
            "blockers",
            "warnings",
            "evidence",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_row_keys": [
            "position_id",
            "position_key",
            "symbol",
            "tradingsymbol",
            "instrument_token",
            "strategy",
            "net_quantity",
            "side",
            "average_entry_price",
            "mark_price",
            "unrealized_pnl",
            "notional_value",
            "row_status",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_summary_keys": [
            "position_count",
            "open_position_count",
            "valued_position_count",
            "missing_mark_count",
            "total_unrealized_pnl",
            "gross_notional_value",
            "net_quantity_abs",
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
            "controlled_mark_inputs_only",
            "unrealized_mtm_only",
            "no_realized_pnl",
            "no_fees",
            "no_slippage_tracker",
            "no_broker_execution",
            "no_live_orders",
            "no_ui",
        ],
    }


def build_paper_mtm_pnl(
    *,
    ledger: dict[str, Any] | None,
    marks: dict[str, Any] | None,
    now_epoch: float | None = None,
    max_mark_age_sec: float = 5.0,
    ts_epoch: float | None = None,
) -> PaperMtmPnlResult:
    blockers, warnings = validate_paper_mtm_pnl_inputs(
        ledger=ledger,
        marks=marks,
        now_epoch=now_epoch,
        max_mark_age_sec=max_mark_age_sec,
    )
    evidence = _tracker_evidence(ledger=ledger, marks=marks, now_epoch=now_epoch, max_mark_age_sec=max_mark_age_sec)
    if blockers:
        return PaperMtmPnlResult(
            valued=False,
            status=PaperMtmPnlStatus.BLOCKED,
            rows=[],
            summary=_empty_summary(),
            blockers=blockers,
            warnings=warnings,
            evidence=evidence,
        )

    positions = _positions(ledger)
    if not positions:
        return PaperMtmPnlResult(
            valued=True,
            status=PaperMtmPnlStatus.EMPTY,
            rows=[],
            summary=_empty_summary(),
            warnings=_dedupe(warnings + ["PAPER_POSITION_LEDGER_EMPTY"]),
            evidence=evidence,
        )

    rows: list[dict[str, Any]] = []
    for position in positions.values():
        rows.append(_mtm_row(position=position, marks=marks or {}, ts_epoch=ts_epoch))

    summary = _summary(rows)
    status = PaperMtmPnlStatus.DEGRADED_MISSING_MARK if summary["missing_mark_count"] else PaperMtmPnlStatus.VALUED
    if summary["missing_mark_count"]:
        warnings.append("MISSING_MARK_FOR_OPEN_POSITION")

    return PaperMtmPnlResult(
        valued=status == PaperMtmPnlStatus.VALUED,
        status=status,
        rows=rows,
        summary=summary,
        warnings=_dedupe(warnings),
        evidence=evidence,
    )


def validate_paper_mtm_pnl_inputs(
    *,
    ledger: dict[str, Any] | None,
    marks: dict[str, Any] | None,
    now_epoch: float | None = None,
    max_mark_age_sec: float = 5.0,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    ledger_payload = ledger if isinstance(ledger, dict) else {}
    marks_payload = marks if isinstance(marks, dict) else {}

    if not ledger_payload:
        blockers.append("PAPER_POSITION_LEDGER_REQUIRED")
    else:
        if ledger_payload.get("ledger_type") != "PAPER_POSITION_LEDGER":
            blockers.append("PAPER_POSITION_LEDGER_TYPE_REQUIRED")
        _validate_safe_flags(ledger_payload, blockers, prefix="PAPER_POSITION_LEDGER")
        if not isinstance(ledger_payload.get("positions"), dict):
            blockers.append("PAPER_POSITION_LEDGER_POSITIONS_INVALID")

    if not marks_payload:
        blockers.append("CONTROLLED_MARK_REQUIRED")
    else:
        mark_source = str(marks_payload.get("source") or "").upper()
        if mark_source not in CONTROLLED_MARK_SOURCES:
            blockers.append("CONTROLLED_MARK_SOURCE_REQUIRED")
        if marks_payload.get("is_order_action") is not False:
            blockers.append("CONTROLLED_MARK_ORDER_FLAG_UNSAFE")
        if marks_payload.get("broker_api_called") is True:
            blockers.append("CONTROLLED_MARK_BROKER_API_CALLED")
        if marks_payload.get("real_order_id") not in (None, ""):
            blockers.append("CONTROLLED_MARK_REAL_ORDER_ID_PRESENT")
        age = _age_sec(marks_payload.get("ts_epoch") or marks_payload.get("mark_ts_epoch"), now_epoch)
        if age is not None and age > max_mark_age_sec:
            blockers.append("CONTROLLED_MARK_STALE")
        elif age is None:
            warnings.append("CONTROLLED_MARK_AGE_UNAVAILABLE")
        _validate_nested_marks(marks_payload, blockers, warnings, now_epoch=now_epoch, max_mark_age_sec=max_mark_age_sec)

    return _dedupe(blockers), _dedupe(warnings)


def _validate_nested_marks(
    marks: dict[str, Any],
    blockers: list[str],
    warnings: list[str],
    *,
    now_epoch: float | None,
    max_mark_age_sec: float,
) -> None:
    nested = marks.get("marks")
    if nested is None:
        warnings.append("CONTROLLED_MARKS_MAP_MISSING")
        return
    if not isinstance(nested, dict):
        blockers.append("CONTROLLED_MARKS_MAP_INVALID")
        return
    for key, raw_mark in nested.items():
        if not isinstance(raw_mark, dict):
            continue
        if raw_mark.get("is_order_action") not in (None, False):
            blockers.append(f"CONTROLLED_MARK_ROW_ORDER_FLAG_UNSAFE:{key}")
        if raw_mark.get("broker_api_called") is True:
            blockers.append(f"CONTROLLED_MARK_ROW_BROKER_API_CALLED:{key}")
        if raw_mark.get("real_order_id") not in (None, ""):
            blockers.append(f"CONTROLLED_MARK_ROW_REAL_ORDER_ID_PRESENT:{key}")
        age = _age_sec(raw_mark.get("ts_epoch") or raw_mark.get("mark_ts_epoch"), now_epoch)
        if age is not None and age > max_mark_age_sec:
            blockers.append(f"CONTROLLED_MARK_ROW_STALE:{key}")


def _mtm_row(*, position: dict[str, Any], marks: dict[str, Any], ts_epoch: float | None) -> dict[str, Any]:
    net_quantity = _int_or_none(position.get("net_quantity")) or 0
    side = str(position.get("side") or "FLAT").upper()
    average_entry_price = _float_or_none(position.get("average_entry_price"))
    mark_price = _mark_price_for_position(position, marks)
    open_position = net_quantity != 0 and side in OPEN_POSITION_SIDES

    row_status = "FLAT"
    unrealized_pnl: float | None = 0.0
    notional_value: float | None = 0.0
    if open_position and average_entry_price is None:
        row_status = "MISSING_AVERAGE_ENTRY_PRICE"
        unrealized_pnl = None
        notional_value = None
    elif open_position and mark_price is None:
        row_status = "MISSING_MARK"
        unrealized_pnl = None
        notional_value = None
    elif open_position:
        multiplier = 1 if side == "LONG" else -1
        unrealized_pnl = round((mark_price - average_entry_price) * abs(net_quantity) * multiplier, 6)
        notional_value = round(abs(net_quantity) * mark_price, 6)
        row_status = "VALUED"

    return {
        "position_id": position.get("position_id"),
        "position_key": position.get("position_key"),
        "symbol": position.get("symbol"),
        "tradingsymbol": position.get("tradingsymbol"),
        "instrument_token": position.get("instrument_token"),
        "strategy": position.get("strategy"),
        "net_quantity": net_quantity,
        "side": side,
        "average_entry_price": average_entry_price,
        "mark_price": mark_price,
        "unrealized_pnl": unrealized_pnl,
        "notional_value": notional_value,
        "row_status": row_status,
        "ts_epoch": ts_epoch,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    open_rows = [row for row in rows if row.get("side") in OPEN_POSITION_SIDES and (_int_or_none(row.get("net_quantity")) or 0) != 0]
    valued_rows = [row for row in open_rows if row.get("row_status") == "VALUED"]
    missing_mark_rows = [row for row in open_rows if row.get("row_status") in {"MISSING_MARK", "MISSING_AVERAGE_ENTRY_PRICE"}]
    return {
        "position_count": len(rows),
        "open_position_count": len(open_rows),
        "valued_position_count": len(valued_rows),
        "missing_mark_count": len(missing_mark_rows),
        "total_unrealized_pnl": round(sum(_float_or_none(row.get("unrealized_pnl")) or 0.0 for row in valued_rows), 6),
        "gross_notional_value": round(sum(_float_or_none(row.get("notional_value")) or 0.0 for row in valued_rows), 6),
        "net_quantity_abs": sum(abs(_int_or_none(row.get("net_quantity")) or 0) for row in open_rows),
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _empty_summary() -> dict[str, Any]:
    return {
        "position_count": 0,
        "open_position_count": 0,
        "valued_position_count": 0,
        "missing_mark_count": 0,
        "total_unrealized_pnl": 0.0,
        "gross_notional_value": 0.0,
        "net_quantity_abs": 0,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _mark_price_for_position(position: dict[str, Any], marks: dict[str, Any]) -> float | None:
    nested = marks.get("marks") if isinstance(marks, dict) else None
    direct_mark = _price_from_mark(marks)
    keys = [
        position.get("position_key"),
        position.get("instrument_token"),
        position.get("tradingsymbol"),
        position.get("symbol"),
        position.get("candidate_id"),
    ]
    if isinstance(nested, dict):
        for key in keys:
            if key in (None, ""):
                continue
            raw = nested.get(str(key))
            if raw is not None:
                return _price_from_mark(raw)
            raw = nested.get(key)
            if raw is not None:
                return _price_from_mark(raw)
    return direct_mark


def _price_from_mark(raw_mark: Any) -> float | None:
    if isinstance(raw_mark, dict):
        for key in ("mark_price", "mark", "ltp", "last", "last_price", "close"):
            value = _float_or_none(raw_mark.get(key))
            if value is not None:
                return value
        return None
    return _float_or_none(raw_mark)


def _positions(ledger: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(ledger, dict):
        return {}
    positions = ledger.get("positions")
    return dict(positions) if isinstance(positions, dict) else {}


def _validate_safe_flags(payload: dict[str, Any], blockers: list[str], *, prefix: str) -> None:
    if payload.get("paper_only") is not True:
        blockers.append(f"{prefix}_NOT_PAPER_ONLY")
    if payload.get("is_order_action") is not False:
        blockers.append(f"{prefix}_ORDER_FLAG_UNSAFE")
    if payload.get("broker_api_called") is not False:
        blockers.append(f"{prefix}_BROKER_API_CALLED")
    if payload.get("real_order_id") not in (None, ""):
        blockers.append(f"{prefix}_REAL_ORDER_ID_PRESENT")


def _tracker_evidence(
    *,
    ledger: dict[str, Any] | None,
    marks: dict[str, Any] | None,
    now_epoch: float | None,
    max_mark_age_sec: float,
) -> dict[str, Any]:
    ledger_payload = ledger if isinstance(ledger, dict) else {}
    marks_payload = marks if isinstance(marks, dict) else {}
    return {
        "ledger_type": ledger_payload.get("ledger_type"),
        "position_count": len(ledger_payload.get("positions") or {}) if isinstance(ledger_payload.get("positions"), dict) else 0,
        "mark_source": marks_payload.get("source"),
        "mark_ts_epoch": marks_payload.get("ts_epoch") or marks_payload.get("mark_ts_epoch"),
        "mark_age_sec": _age_sec(marks_payload.get("ts_epoch") or marks_payload.get("mark_ts_epoch"), now_epoch),
        "max_mark_age_sec": max_mark_age_sec,
        "controlled_mark_only": True,
        "unrealized_mtm_only": True,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _age_sec(ts_epoch: Any, now_epoch: float | None) -> float | None:
    ts = _float_or_none(ts_epoch)
    if ts is None or now_epoch is None:
        return None
    return max(float(now_epoch) - ts, 0.0)


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

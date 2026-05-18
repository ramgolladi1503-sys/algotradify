from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


PAPER_PERFORMANCE_SNAPSHOT_SCHEMA_VERSION = "1.0"


class PaperPerformanceSnapshotStatus(StrEnum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperPerformanceSnapshotResult:
    created: bool
    status: PaperPerformanceSnapshotStatus
    snapshot: dict[str, Any] | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: str = PAPER_PERFORMANCE_SNAPSHOT_SCHEMA_VERSION

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
            "snapshot_type": "PAPER_PERFORMANCE_SNAPSHOT",
            "created": self.created,
            "status": self.status.value,
            "snapshot": dict(self.snapshot) if self.snapshot else None,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_performance_snapshot_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_PERFORMANCE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_type": "PAPER_PERFORMANCE_SNAPSHOT",
        "consumes": [
            "PAPER_POSITION_LEDGER",
            "PAPER_MTM_PNL_TRACKER",
            "PAPER_REALIZED_PNL_LEDGER",
            "PAPER_SLIPPAGE_FILL_QUALITY",
        ],
        "statuses": [status.value for status in PaperPerformanceSnapshotStatus],
        "required_result_keys": [
            "schema_version",
            "snapshot_type",
            "created",
            "status",
            "snapshot",
            "blockers",
            "warnings",
            "evidence",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_snapshot_keys": [
            "schema_version",
            "snapshot_type",
            "status",
            "summary",
            "positions",
            "pnl",
            "slippage",
            "diagnostics",
            "source_statuses",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_summary_keys": [
            "position_count",
            "open_position_count",
            "net_quantity_abs",
            "total_unrealized_pnl",
            "total_realized_pnl",
            "combined_pnl",
            "gross_notional_value",
            "slippage_event_count",
            "total_slippage_amount",
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
            "paper_only",
            "read_only_aggregation_only",
            "no_broker_execution",
            "no_live_orders",
            "no_ui",
            "no_persistence",
            "no_order_decisions",
        ],
    }


def build_paper_performance_snapshot(
    *,
    position_ledger: dict[str, Any] | None,
    mtm_pnl: dict[str, Any] | None = None,
    realized_pnl: dict[str, Any] | None = None,
    slippage: dict[str, Any] | None = None,
    ts_epoch: float | None = None,
) -> PaperPerformanceSnapshotResult:
    blockers, warnings = validate_paper_performance_snapshot_inputs(
        position_ledger=position_ledger,
        mtm_pnl=mtm_pnl,
        realized_pnl=realized_pnl,
        slippage=slippage,
    )
    evidence = _evidence(position_ledger=position_ledger, mtm_pnl=mtm_pnl, realized_pnl=realized_pnl, slippage=slippage)
    if blockers:
        return PaperPerformanceSnapshotResult(
            created=False,
            status=PaperPerformanceSnapshotStatus.BLOCKED,
            blockers=blockers,
            warnings=warnings,
            evidence=evidence,
        )

    positions = _positions_block(position_ledger)
    pnl = _pnl_block(mtm_pnl=mtm_pnl, realized_pnl=realized_pnl)
    slippage_block = _slippage_block(slippage)
    diagnostics = _diagnostics(position_ledger=position_ledger, mtm_pnl=mtm_pnl, realized_pnl=realized_pnl, slippage=slippage, warnings=warnings)
    summary = _summary(positions=positions, pnl=pnl, slippage=slippage_block)
    status = _snapshot_status(summary=summary, diagnostics=diagnostics)
    snapshot = {
        "schema_version": PAPER_PERFORMANCE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_type": "PAPER_PERFORMANCE_SNAPSHOT",
        "status": status.value,
        "ts_epoch": ts_epoch,
        "summary": summary,
        "positions": positions,
        "pnl": pnl,
        "slippage": slippage_block,
        "diagnostics": diagnostics,
        "source_statuses": _source_statuses(position_ledger=position_ledger, mtm_pnl=mtm_pnl, realized_pnl=realized_pnl, slippage=slippage),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    return PaperPerformanceSnapshotResult(
        created=True,
        status=status,
        snapshot=snapshot,
        warnings=_dedupe(warnings),
        evidence=evidence,
    )


def validate_paper_performance_snapshot_inputs(
    *,
    position_ledger: dict[str, Any] | None,
    mtm_pnl: dict[str, Any] | None = None,
    realized_pnl: dict[str, Any] | None = None,
    slippage: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if not isinstance(position_ledger, dict) or not position_ledger:
        blockers.append("PAPER_POSITION_LEDGER_REQUIRED")
    else:
        if position_ledger.get("ledger_type") != "PAPER_POSITION_LEDGER":
            blockers.append("PAPER_POSITION_LEDGER_TYPE_REQUIRED")
        _validate_safe_flags(position_ledger, blockers, prefix="PAPER_POSITION_LEDGER", require_read_only=False)
        if not isinstance(position_ledger.get("positions"), dict):
            blockers.append("PAPER_POSITION_LEDGER_POSITIONS_INVALID")

    _validate_optional_source(
        mtm_pnl,
        expected_key="tracker_type",
        expected_value="PAPER_MTM_PNL_TRACKER",
        prefix="PAPER_MTM_PNL_TRACKER",
        blockers=blockers,
        warnings=warnings,
    )
    _validate_optional_source(
        realized_pnl,
        expected_key="ledger_type",
        expected_value="PAPER_REALIZED_PNL_LEDGER",
        prefix="PAPER_REALIZED_PNL_LEDGER",
        blockers=blockers,
        warnings=warnings,
    )
    _validate_optional_source(
        slippage,
        expected_key="report_type",
        expected_value="PAPER_SLIPPAGE_FILL_QUALITY",
        prefix="PAPER_SLIPPAGE_FILL_QUALITY",
        blockers=blockers,
        warnings=warnings,
    )

    if not isinstance(mtm_pnl, dict) or not mtm_pnl:
        warnings.append("PAPER_MTM_PNL_TRACKER_MISSING")
    if not isinstance(realized_pnl, dict) or not realized_pnl:
        warnings.append("PAPER_REALIZED_PNL_LEDGER_MISSING")
    if not isinstance(slippage, dict) or not slippage:
        warnings.append("PAPER_SLIPPAGE_FILL_QUALITY_MISSING")

    return _dedupe(blockers), _dedupe(warnings)


def _validate_optional_source(
    source: dict[str, Any] | None,
    *,
    expected_key: str,
    expected_value: str,
    prefix: str,
    blockers: list[str],
    warnings: list[str],
) -> None:
    if source is None:
        return
    if not isinstance(source, dict) or not source:
        warnings.append(f"{prefix}_EMPTY")
        return
    if source.get(expected_key) != expected_value:
        blockers.append(f"{prefix}_TYPE_REQUIRED")
    _validate_safe_flags(source, blockers, prefix=prefix, require_read_only=False)


def _validate_safe_flags(payload: dict[str, Any], blockers: list[str], *, prefix: str, require_read_only: bool) -> None:
    if payload.get("paper_only") is not True:
        blockers.append(f"{prefix}_NOT_PAPER_ONLY")
    if require_read_only and payload.get("read_only") is not True:
        blockers.append(f"{prefix}_NOT_READ_ONLY")
    if payload.get("is_order_action") is not False:
        blockers.append(f"{prefix}_ORDER_FLAG_UNSAFE")
    if payload.get("broker_api_called") is not False:
        blockers.append(f"{prefix}_BROKER_API_CALLED")
    if payload.get("real_order_id") not in (None, ""):
        blockers.append(f"{prefix}_REAL_ORDER_ID_PRESENT")


def _positions_block(position_ledger: dict[str, Any] | None) -> dict[str, Any]:
    positions = position_ledger.get("positions") if isinstance(position_ledger, dict) else {}
    positions = positions if isinstance(positions, dict) else {}
    rows = [dict(position) for position in positions.values() if isinstance(position, dict)]
    open_rows = [row for row in rows if (_int_or_none(row.get("net_quantity")) or 0) != 0]
    long_count = len([row for row in open_rows if str(row.get("side") or "").upper() == "LONG"])
    short_count = len([row for row in open_rows if str(row.get("side") or "").upper() == "SHORT"])
    return {
        "position_count": len(rows),
        "open_position_count": len(open_rows),
        "long_position_count": long_count,
        "short_position_count": short_count,
        "flat_position_count": len(rows) - len(open_rows),
        "net_quantity_abs": sum(abs(_int_or_none(row.get("net_quantity")) or 0) for row in open_rows),
        "positions": rows,
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _pnl_block(*, mtm_pnl: dict[str, Any] | None, realized_pnl: dict[str, Any] | None) -> dict[str, Any]:
    mtm_summary = mtm_pnl.get("summary") if isinstance(mtm_pnl, dict) else {}
    realized_summary = realized_pnl.get("summary") if isinstance(realized_pnl, dict) else {}
    mtm_summary = mtm_summary if isinstance(mtm_summary, dict) else {}
    realized_summary = realized_summary if isinstance(realized_summary, dict) else {}
    unrealized = _float_or_zero(mtm_summary.get("total_unrealized_pnl"))
    realized = _float_or_zero(realized_summary.get("total_realized_pnl"))
    return {
        "total_unrealized_pnl": unrealized,
        "total_realized_pnl": realized,
        "combined_pnl": round(unrealized + realized, 6),
        "gross_notional_value": _float_or_zero(mtm_summary.get("gross_notional_value")),
        "valued_position_count": _int_or_none(mtm_summary.get("valued_position_count")) or 0,
        "missing_mark_count": _int_or_none(mtm_summary.get("missing_mark_count")) or 0,
        "realized_event_count": _int_or_none(realized_summary.get("event_count")) or 0,
        "winning_event_count": _int_or_none(realized_summary.get("winning_event_count")) or 0,
        "losing_event_count": _int_or_none(realized_summary.get("losing_event_count")) or 0,
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _slippage_block(slippage: dict[str, Any] | None) -> dict[str, Any]:
    summary = slippage.get("summary") if isinstance(slippage, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    return {
        "slippage_event_count": _int_or_none(summary.get("event_count")) or 0,
        "measured_quantity": _int_or_none(summary.get("measured_quantity")) or 0,
        "total_slippage_amount": _float_or_zero(summary.get("total_slippage_amount")),
        "average_slippage_per_unit": _float_or_zero(summary.get("average_slippage_per_unit")),
        "weighted_average_slippage_bps": _float_or_zero(summary.get("weighted_average_slippage_bps")),
        "favorable_event_count": _int_or_none(summary.get("favorable_event_count")) or 0,
        "unfavorable_event_count": _int_or_none(summary.get("unfavorable_event_count")) or 0,
        "flat_event_count": _int_or_none(summary.get("flat_event_count")) or 0,
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _summary(*, positions: dict[str, Any], pnl: dict[str, Any], slippage: dict[str, Any]) -> dict[str, Any]:
    return {
        "position_count": positions["position_count"],
        "open_position_count": positions["open_position_count"],
        "net_quantity_abs": positions["net_quantity_abs"],
        "total_unrealized_pnl": pnl["total_unrealized_pnl"],
        "total_realized_pnl": pnl["total_realized_pnl"],
        "combined_pnl": pnl["combined_pnl"],
        "gross_notional_value": pnl["gross_notional_value"],
        "slippage_event_count": slippage["slippage_event_count"],
        "total_slippage_amount": slippage["total_slippage_amount"],
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _diagnostics(
    *,
    position_ledger: dict[str, Any] | None,
    mtm_pnl: dict[str, Any] | None,
    realized_pnl: dict[str, Any] | None,
    slippage: dict[str, Any] | None,
    warnings: list[str],
) -> dict[str, Any]:
    missing_sources = []
    degraded_sources = []
    for name, source in (
        ("mtm_pnl", mtm_pnl),
        ("realized_pnl", realized_pnl),
        ("slippage", slippage),
    ):
        if not isinstance(source, dict) or not source:
            missing_sources.append(name)
        elif str(source.get("status") or "").upper().startswith("DEGRADED"):
            degraded_sources.append(name)
    return {
        "missing_sources": missing_sources,
        "degraded_sources": degraded_sources,
        "warning_count": len(_dedupe(warnings)),
        "position_source_present": isinstance(position_ledger, dict) and bool(position_ledger),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _snapshot_status(*, summary: dict[str, Any], diagnostics: dict[str, Any]) -> PaperPerformanceSnapshotStatus:
    if summary["position_count"] == 0 and summary["total_realized_pnl"] == 0 and summary["slippage_event_count"] == 0:
        return PaperPerformanceSnapshotStatus.EMPTY
    if diagnostics["missing_sources"] or diagnostics["degraded_sources"]:
        return PaperPerformanceSnapshotStatus.DEGRADED
    return PaperPerformanceSnapshotStatus.READY


def _source_statuses(
    *,
    position_ledger: dict[str, Any] | None,
    mtm_pnl: dict[str, Any] | None,
    realized_pnl: dict[str, Any] | None,
    slippage: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "position_ledger": _source_status(position_ledger, type_key="ledger_type"),
        "mtm_pnl": _source_status(mtm_pnl, type_key="tracker_type"),
        "realized_pnl": _source_status(realized_pnl, type_key="ledger_type"),
        "slippage": _source_status(slippage, type_key="report_type"),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _source_status(source: dict[str, Any] | None, *, type_key: str) -> dict[str, Any]:
    if not isinstance(source, dict) or not source:
        return {"present": False, "type": None, "status": "MISSING"}
    return {"present": True, "type": source.get(type_key), "status": source.get("status")}


def _evidence(
    *,
    position_ledger: dict[str, Any] | None,
    mtm_pnl: dict[str, Any] | None,
    realized_pnl: dict[str, Any] | None,
    slippage: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "position_ledger_type": position_ledger.get("ledger_type") if isinstance(position_ledger, dict) else None,
        "mtm_tracker_type": mtm_pnl.get("tracker_type") if isinstance(mtm_pnl, dict) else None,
        "realized_ledger_type": realized_pnl.get("ledger_type") if isinstance(realized_pnl, dict) else None,
        "slippage_report_type": slippage.get("report_type") if isinstance(slippage, dict) else None,
        "read_only_aggregation_only": True,
        "paper_only": True,
        "read_only": True,
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


def _float_or_zero(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
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

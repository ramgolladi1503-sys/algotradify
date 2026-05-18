from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from broker_contract.readiness import BrokerContractReadiness, BrokerContractReadinessStatus


INSTRUMENT_RESOLUTION_HEALTH_SCHEMA_VERSION = "1.0"


class InstrumentResolutionHealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED_FALLBACK = "DEGRADED_FALLBACK"
    BLOCKED_UNRESOLVED = "BLOCKED_UNRESOLVED"
    EMPTY = "EMPTY"


@dataclass(frozen=True)
class InstrumentResolutionHealthPanel:
    status: InstrumentResolutionHealthStatus
    summary: dict[str, Any]
    rows: list[dict[str, Any]]
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = INSTRUMENT_RESOLUTION_HEALTH_SCHEMA_VERSION

    @property
    def read_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "panel_type": "INSTRUMENT_RESOLUTION_HEALTH_PANEL",
            "status": self.status.value,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "summary": dict(self.summary),
            "rows": [dict(row) for row in self.rows],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


def instrument_resolution_health_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": INSTRUMENT_RESOLUTION_HEALTH_SCHEMA_VERSION,
        "panel_type": "INSTRUMENT_RESOLUTION_HEALTH_PANEL",
        "required_keys": [
            "schema_version",
            "panel_type",
            "status",
            "read_only",
            "is_order_action",
            "summary",
            "rows",
            "blockers",
            "warnings",
        ],
        "summary_required_keys": [
            "record_count",
            "resolved_count",
            "unresolved_count",
            "exact_count",
            "fallback_count",
            "missing_token_count",
            "expired_or_mismatched_count",
            "blocked_count",
            "warning_count",
            "read_only",
            "is_order_action",
        ],
        "row_required_keys": [
            "candidate_id",
            "symbol",
            "strategy_id",
            "readiness_status",
            "resolved",
            "instrument_token",
            "fallback_used",
            "fallback_distance",
            "resolution_source",
            "tradingsymbol",
            "expiry",
            "strike",
            "option_type",
            "exchange",
            "blockers",
            "warnings",
            "read_only",
            "is_order_action",
        ],
        "safe_flags": {"read_only": True, "is_order_action": False},
    }


def build_instrument_resolution_health_panel(records: list[Any] | None) -> InstrumentResolutionHealthPanel:
    readiness_rows = [_to_row(record) for record in records or []]
    summary = _summary(readiness_rows)
    blockers = _panel_blockers(summary)
    warnings = _panel_warnings(readiness_rows, summary)
    return InstrumentResolutionHealthPanel(
        status=_status_from_summary(summary),
        summary=summary,
        rows=readiness_rows,
        blockers=blockers,
        warnings=warnings,
    )


def _to_row(record: Any) -> dict[str, Any]:
    payload = record.to_dict() if isinstance(record, BrokerContractReadiness) else dict(record or {})
    request = payload.get("request") if isinstance(payload.get("request"), dict) else {}
    resolution = payload.get("resolution") if isinstance(payload.get("resolution"), dict) else {}
    instrument = resolution.get("instrument") if isinstance(resolution.get("instrument"), dict) else {}
    resolution_source = _resolution_source(payload, resolution)
    blockers = _dedupe(
        list(payload.get("blockers") or [])
        + _resolution_mismatch_blockers(request, instrument, resolution_source=resolution_source)
    )
    warnings = _dedupe(list(payload.get("warnings") or []))
    return {
        "candidate_id": payload.get("candidate_id"),
        "symbol": payload.get("symbol") or request.get("symbol") or instrument.get("symbol"),
        "strategy_id": payload.get("strategy_id"),
        "readiness_status": payload.get("readiness_status"),
        "resolved": payload.get("resolved") is True,
        "instrument_token": payload.get("instrument_token") or resolution.get("instrument_token") or instrument.get("instrument_token"),
        "fallback_used": payload.get("fallback_used") is True,
        "fallback_distance": payload.get("fallback_distance"),
        "resolution_source": resolution_source,
        "tradingsymbol": resolution.get("tradingsymbol") or instrument.get("tradingsymbol"),
        "expiry": instrument.get("expiry") or request.get("expiry"),
        "strike": instrument.get("strike") if instrument.get("strike") not in (None, "") else request.get("strike"),
        "option_type": instrument.get("instrument_type") or instrument.get("option_type") or request.get("option_type"),
        "exchange": instrument.get("exchange") or request.get("exchange"),
        "blockers": blockers,
        "warnings": warnings,
        "read_only": True,
        "is_order_action": False,
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    record_count = len(rows)
    resolved_count = sum(1 for row in rows if row["resolved"] is True)
    fallback_count = sum(1 for row in rows if row["fallback_used"] is True or row["resolution_source"] == "FALLBACK")
    exact_count = sum(1 for row in rows if row["resolution_source"] == "EXACT")
    missing_token_count = sum(1 for row in rows if row.get("instrument_token") in (None, ""))
    expired_or_mismatched_count = sum(1 for row in rows if any(str(blocker).startswith("INSTRUMENT_MISMATCH_") for blocker in row.get("blockers", [])))
    blocked_count = sum(1 for row in rows if row["resolved"] is not True or row.get("blockers"))
    warning_count = sum(len(row.get("warnings") or []) for row in rows)
    return {
        "record_count": record_count,
        "resolved_count": resolved_count,
        "unresolved_count": record_count - resolved_count,
        "exact_count": exact_count,
        "fallback_count": fallback_count,
        "missing_token_count": missing_token_count,
        "expired_or_mismatched_count": expired_or_mismatched_count,
        "blocked_count": blocked_count,
        "warning_count": warning_count,
        "read_only": True,
        "is_order_action": False,
    }


def _status_from_summary(summary: dict[str, Any]) -> InstrumentResolutionHealthStatus:
    if summary["record_count"] == 0:
        return InstrumentResolutionHealthStatus.EMPTY
    if summary["unresolved_count"] or summary["missing_token_count"] or summary["expired_or_mismatched_count"]:
        return InstrumentResolutionHealthStatus.BLOCKED_UNRESOLVED
    if summary["fallback_count"] or summary["warning_count"]:
        return InstrumentResolutionHealthStatus.DEGRADED_FALLBACK
    return InstrumentResolutionHealthStatus.HEALTHY


def _panel_blockers(summary: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if summary["record_count"] == 0:
        blockers.append("NO_INSTRUMENT_RESOLUTION_RECORDS")
    if summary["unresolved_count"]:
        blockers.append("UNRESOLVED_INSTRUMENTS_PRESENT")
    if summary["missing_token_count"]:
        blockers.append("MISSING_INSTRUMENT_TOKENS_PRESENT")
    if summary["expired_or_mismatched_count"]:
        blockers.append("EXPIRED_OR_MISMATCHED_INSTRUMENTS_PRESENT")
    return blockers


def _panel_warnings(rows: list[dict[str, Any]], summary: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if summary["fallback_count"]:
        warnings.append("FALLBACK_INSTRUMENT_RESOLUTION_PRESENT")
    if summary["warning_count"]:
        warnings.append("ROW_WARNINGS_PRESENT")
    for row in rows:
        for warning in row.get("warnings") or []:
            text = f"{row.get('candidate_id')}:{warning}"
            if text not in warnings:
                warnings.append(text)
    return warnings


def _resolution_source(payload: dict[str, Any], resolution: dict[str, Any]) -> str:
    status = str(resolution.get("status") or payload.get("readiness_status") or "UNKNOWN").upper()
    if "EXACT" in status:
        return "EXACT"
    if "FALLBACK" in status or payload.get("fallback_used") is True:
        return "FALLBACK"
    if "NOT_FOUND" in status:
        return "NOT_FOUND"
    if "MISSING" in status:
        return "MISSING_REQUEST"
    if "COVERAGE" in status:
        return "COVERAGE_FAILED"
    return status or "UNKNOWN"


def _resolution_mismatch_blockers(
    request: dict[str, Any],
    instrument: dict[str, Any],
    *,
    resolution_source: str,
) -> list[str]:
    blockers: list[str] = []
    if not instrument:
        return blockers
    checks = {
        "EXPIRY": (request.get("expiry"), instrument.get("expiry")),
        "STRIKE": (_to_float(request.get("strike")), _to_float(instrument.get("strike"))),
        "OPTION_TYPE": (_upper(request.get("option_type")), _upper(instrument.get("instrument_type") or instrument.get("option_type"))),
        "EXCHANGE": (_upper(request.get("exchange")), _upper(instrument.get("exchange"))),
    }
    for label, (requested, resolved) in checks.items():
        if resolution_source == "FALLBACK" and label == "STRIKE":
            continue
        if requested not in (None, "") and resolved not in (None, "") and requested != resolved:
            blockers.append(f"INSTRUMENT_MISMATCH_{label}")
    return blockers


def _upper(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).upper()


def _to_float(value: Any) -> float | None:
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

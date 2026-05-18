from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


OPTION_CHAIN_DEPTH_MONITOR_SCHEMA_VERSION = "1.0"
DEFAULT_MIN_SIDE_COUNT = 1
DEFAULT_MIN_TOTAL_DEPTH = 100.0
DEFAULT_MAX_DEPTH_AGE_SEC = 5.0
DEFAULT_MAX_IMBALANCE_RATIO = 3.0


class OptionChainDepthQualityStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BLOCKED_MISSING_SIDE = "BLOCKED_MISSING_SIDE"
    BLOCKED_ZERO_SIDE = "BLOCKED_ZERO_SIDE"
    BLOCKED_SHALLOW_DEPTH = "BLOCKED_SHALLOW_DEPTH"
    BLOCKED_STALE_DEPTH = "BLOCKED_STALE_DEPTH"
    BLOCKED_DEPTH_IMBALANCE = "BLOCKED_DEPTH_IMBALANCE"
    EMPTY = "EMPTY"


@dataclass(frozen=True)
class OptionChainDepthQualityMonitor:
    status: OptionChainDepthQualityStatus
    summary: dict[str, Any]
    side_quality: dict[str, Any]
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = OPTION_CHAIN_DEPTH_MONITOR_SCHEMA_VERSION

    @property
    def read_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "monitor_type": "OPTION_CHAIN_DEPTH_QUALITY_MONITOR",
            "status": self.status.value,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "summary": dict(self.summary),
            "side_quality": dict(self.side_quality),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


def option_chain_depth_quality_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": OPTION_CHAIN_DEPTH_MONITOR_SCHEMA_VERSION,
        "monitor_type": "OPTION_CHAIN_DEPTH_QUALITY_MONITOR",
        "required_keys": [
            "schema_version",
            "monitor_type",
            "status",
            "read_only",
            "is_order_action",
            "summary",
            "side_quality",
            "blockers",
            "warnings",
        ],
        "summary_required_keys": [
            "ce_count",
            "pe_count",
            "ce_depth",
            "pe_depth",
            "total_depth",
            "depth_age_sec",
            "min_side_count",
            "min_total_depth",
            "max_depth_age_sec",
            "max_imbalance_ratio",
            "imbalance_ratio",
            "missing_side_count",
            "zero_side_count",
            "shallow_depth_count",
            "stale_depth_count",
            "imbalance_count",
            "read_only",
            "is_order_action",
        ],
        "side_quality_required_keys": [
            "ce_available",
            "pe_available",
            "ce_depth_ok",
            "pe_depth_ok",
            "depth_fresh",
            "imbalance_ok",
        ],
        "safe_flags": {"read_only": True, "is_order_action": False},
        "default_thresholds": {
            "min_side_count": DEFAULT_MIN_SIDE_COUNT,
            "min_total_depth": DEFAULT_MIN_TOTAL_DEPTH,
            "max_depth_age_sec": DEFAULT_MAX_DEPTH_AGE_SEC,
            "max_imbalance_ratio": DEFAULT_MAX_IMBALANCE_RATIO,
        },
    }


def build_option_chain_depth_quality_monitor(
    row: dict[str, Any] | None,
    *,
    min_side_count: int = DEFAULT_MIN_SIDE_COUNT,
    min_total_depth: float = DEFAULT_MIN_TOTAL_DEPTH,
    max_depth_age_sec: float = DEFAULT_MAX_DEPTH_AGE_SEC,
    max_imbalance_ratio: float = DEFAULT_MAX_IMBALANCE_RATIO,
) -> OptionChainDepthQualityMonitor:
    if not isinstance(row, dict):
        row = {}

    ce_count = _int(_first_present(row, "ce_count", "call_count", "option_ce_count"))
    pe_count = _int(_first_present(row, "pe_count", "put_count", "option_pe_count"))
    ce_depth = _num(_first_present(row, "ce_depth", "call_depth", "option_ce_depth", "ce_total_depth"))
    pe_depth = _num(_first_present(row, "pe_depth", "put_depth", "option_pe_depth", "pe_total_depth"))
    depth_age_sec = _num(_first_present(row, "depth_age_sec", "option_chain_age_sec", "chain_age_sec", "market_depth_age_sec"))

    ce_available = ce_count is not None and ce_count >= min_side_count
    pe_available = pe_count is not None and pe_count >= min_side_count
    ce_depth_ok = ce_depth is not None and ce_depth > 0
    pe_depth_ok = pe_depth is not None and pe_depth > 0
    total_depth = (ce_depth or 0.0) + (pe_depth or 0.0)
    depth_fresh = depth_age_sec is not None and depth_age_sec <= max_depth_age_sec
    imbalance_ratio = _imbalance_ratio(ce_depth, pe_depth)
    imbalance_ok = imbalance_ratio is not None and imbalance_ratio <= max_imbalance_ratio

    blockers: list[str] = []
    warnings: list[str] = []

    if not row:
        blockers.append("NO_OPTION_CHAIN_DEPTH_DATA")

    missing_side_count = 0
    if ce_count is None:
        missing_side_count += 1
        blockers.append("MISSING_CE_SIDE_COUNT")
    if pe_count is None:
        missing_side_count += 1
        blockers.append("MISSING_PE_SIDE_COUNT")

    zero_side_count = 0
    if ce_count == 0:
        zero_side_count += 1
        blockers.append("ZERO_CE_SIDE_COUNT")
    if pe_count == 0:
        zero_side_count += 1
        blockers.append("ZERO_PE_SIDE_COUNT")

    shallow_depth_count = 0
    if ce_depth is None:
        shallow_depth_count += 1
        blockers.append("MISSING_CE_DEPTH")
    elif ce_depth <= 0:
        shallow_depth_count += 1
        blockers.append("ZERO_CE_DEPTH")
    if pe_depth is None:
        shallow_depth_count += 1
        blockers.append("MISSING_PE_DEPTH")
    elif pe_depth <= 0:
        shallow_depth_count += 1
        blockers.append("ZERO_PE_DEPTH")
    if total_depth < min_total_depth:
        shallow_depth_count += 1
        blockers.append("TOTAL_DEPTH_BELOW_MINIMUM")

    stale_depth_count = 0
    if depth_age_sec is None:
        stale_depth_count += 1
        blockers.append("MISSING_DEPTH_AGE")
    elif depth_age_sec > max_depth_age_sec:
        stale_depth_count += 1
        blockers.append("STALE_OPTION_DEPTH")

    imbalance_count = 0
    if imbalance_ratio is None:
        warnings.append("DEPTH_IMBALANCE_UNAVAILABLE")
    elif imbalance_ratio > max_imbalance_ratio:
        imbalance_count = 1
        blockers.append("OPTION_DEPTH_IMBALANCE")

    summary = {
        "ce_count": ce_count,
        "pe_count": pe_count,
        "ce_depth": ce_depth,
        "pe_depth": pe_depth,
        "total_depth": total_depth,
        "depth_age_sec": depth_age_sec,
        "min_side_count": min_side_count,
        "min_total_depth": min_total_depth,
        "max_depth_age_sec": max_depth_age_sec,
        "max_imbalance_ratio": max_imbalance_ratio,
        "imbalance_ratio": imbalance_ratio,
        "missing_side_count": missing_side_count,
        "zero_side_count": zero_side_count,
        "shallow_depth_count": shallow_depth_count,
        "stale_depth_count": stale_depth_count,
        "imbalance_count": imbalance_count,
        "read_only": True,
        "is_order_action": False,
    }
    side_quality = {
        "ce_available": ce_available,
        "pe_available": pe_available,
        "ce_depth_ok": ce_depth_ok,
        "pe_depth_ok": pe_depth_ok,
        "depth_fresh": depth_fresh,
        "imbalance_ok": imbalance_ok,
    }

    return OptionChainDepthQualityMonitor(
        status=_status_from_summary(summary, blockers),
        summary=summary,
        side_quality=side_quality,
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
    )


def _status_from_summary(summary: dict[str, Any], blockers: list[str]) -> OptionChainDepthQualityStatus:
    if "NO_OPTION_CHAIN_DEPTH_DATA" in blockers:
        return OptionChainDepthQualityStatus.EMPTY
    if summary["missing_side_count"]:
        return OptionChainDepthQualityStatus.BLOCKED_MISSING_SIDE
    if summary["zero_side_count"]:
        return OptionChainDepthQualityStatus.BLOCKED_ZERO_SIDE
    if summary["stale_depth_count"]:
        return OptionChainDepthQualityStatus.BLOCKED_STALE_DEPTH
    if summary["shallow_depth_count"]:
        return OptionChainDepthQualityStatus.BLOCKED_SHALLOW_DEPTH
    if summary["imbalance_count"]:
        return OptionChainDepthQualityStatus.BLOCKED_DEPTH_IMBALANCE
    if blockers:
        return OptionChainDepthQualityStatus.DEGRADED
    return OptionChainDepthQualityStatus.HEALTHY


def _imbalance_ratio(ce_depth: float | None, pe_depth: float | None) -> float | None:
    if ce_depth is None or pe_depth is None or ce_depth <= 0 or pe_depth <= 0:
        return None
    larger = max(ce_depth, pe_depth)
    smaller = min(ce_depth, pe_depth)
    return larger / smaller


def _first_present(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
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

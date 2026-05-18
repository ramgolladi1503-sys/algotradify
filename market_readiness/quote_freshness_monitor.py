from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from market_readiness.live_snapshot import (
    LiveMarketDataSnapshot,
    LiveMarketDataSnapshotStatus,
    build_live_market_data_snapshot,
)


QUOTE_FRESHNESS_MONITOR_SCHEMA_VERSION = "1.0"


class QuoteFreshnessMonitorStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    EMPTY = "EMPTY"


@dataclass(frozen=True)
class QuoteFreshnessRuntimeMonitor:
    snapshots: list[LiveMarketDataSnapshot]
    status: QuoteFreshnessMonitorStatus
    summary: dict[str, Any]
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = QUOTE_FRESHNESS_MONITOR_SCHEMA_VERSION

    @property
    def read_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "monitor_type": "QUOTE_FRESHNESS_RUNTIME_MONITOR",
            "status": self.status.value,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "summary": dict(self.summary),
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


def quote_freshness_runtime_monitor_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": QUOTE_FRESHNESS_MONITOR_SCHEMA_VERSION,
        "monitor_type": "QUOTE_FRESHNESS_RUNTIME_MONITOR",
        "required_keys": [
            "schema_version",
            "monitor_type",
            "status",
            "read_only",
            "is_order_action",
            "summary",
            "snapshots",
            "blockers",
            "warnings",
        ],
        "summary_required_keys": [
            "snapshot_count",
            "ready_count",
            "stale_spot_count",
            "missing_spot_count",
            "fallback_source_count",
            "missing_option_chain_count",
            "stale_option_chain_count",
            "closed_session_count",
            "blocked_count",
            "warning_count",
            "fresh_ratio",
            "read_only",
            "is_order_action",
        ],
        "safe_flags": {"read_only": True, "is_order_action": False},
    }


def build_quote_freshness_runtime_monitor(
    rows: list[dict[str, Any] | LiveMarketDataSnapshot] | None,
    **snapshot_kwargs: Any,
) -> QuoteFreshnessRuntimeMonitor:
    source_rows = rows or []
    snapshots = [
        row if isinstance(row, LiveMarketDataSnapshot) else build_live_market_data_snapshot(row, **snapshot_kwargs)
        for row in source_rows
    ]
    summary = _summary(snapshots)
    blockers = _monitor_blockers(summary)
    warnings = _monitor_warnings(snapshots, summary)
    return QuoteFreshnessRuntimeMonitor(
        snapshots=snapshots,
        status=_monitor_status(summary, blockers),
        summary=summary,
        blockers=blockers,
        warnings=warnings,
    )


def _summary(snapshots: list[LiveMarketDataSnapshot]) -> dict[str, Any]:
    snapshot_count = len(snapshots)
    ready_count = sum(1 for snapshot in snapshots if snapshot.status == LiveMarketDataSnapshotStatus.READY)
    stale_spot_count = sum(1 for snapshot in snapshots if snapshot.status == LiveMarketDataSnapshotStatus.BLOCKED_STALE_SPOT)
    missing_spot_count = sum(1 for snapshot in snapshots if snapshot.status == LiveMarketDataSnapshotStatus.BLOCKED_MISSING_SPOT)
    fallback_source_count = sum(1 for snapshot in snapshots if snapshot.status == LiveMarketDataSnapshotStatus.BLOCKED_FALLBACK_SOURCE)
    missing_option_chain_count = sum(1 for snapshot in snapshots if snapshot.status == LiveMarketDataSnapshotStatus.BLOCKED_MISSING_OPTION_CHAIN)
    stale_option_chain_count = sum(1 for snapshot in snapshots if snapshot.status == LiveMarketDataSnapshotStatus.BLOCKED_STALE_OPTION_CHAIN)
    closed_session_count = sum(1 for snapshot in snapshots if snapshot.status == LiveMarketDataSnapshotStatus.BLOCKED_SESSION_CLOSED)
    blocked_count = snapshot_count - ready_count
    warning_count = sum(len(snapshot.warnings) for snapshot in snapshots)
    return {
        "snapshot_count": snapshot_count,
        "ready_count": ready_count,
        "stale_spot_count": stale_spot_count,
        "missing_spot_count": missing_spot_count,
        "fallback_source_count": fallback_source_count,
        "missing_option_chain_count": missing_option_chain_count,
        "stale_option_chain_count": stale_option_chain_count,
        "closed_session_count": closed_session_count,
        "blocked_count": blocked_count,
        "warning_count": warning_count,
        "fresh_ratio": (ready_count / snapshot_count) if snapshot_count else 0.0,
        "read_only": True,
        "is_order_action": False,
    }


def _monitor_blockers(summary: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if summary["snapshot_count"] == 0:
        blockers.append("NO_MARKET_DATA_SNAPSHOTS")
    if summary["missing_spot_count"]:
        blockers.append("MISSING_SPOT_DATA_PRESENT")
    if summary["stale_spot_count"]:
        blockers.append("STALE_SPOT_QUOTES_PRESENT")
    if summary["fallback_source_count"]:
        blockers.append("FALLBACK_MARKET_DATA_SOURCE_PRESENT")
    if summary["missing_option_chain_count"]:
        blockers.append("MISSING_OPTION_CHAIN_PRESENT")
    if summary["stale_option_chain_count"]:
        blockers.append("STALE_OPTION_CHAIN_PRESENT")
    if summary["closed_session_count"]:
        blockers.append("MARKET_SESSION_CLOSED_PRESENT")
    return blockers


def _monitor_warnings(snapshots: list[LiveMarketDataSnapshot], summary: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if summary["warning_count"]:
        warnings.append("SNAPSHOT_WARNINGS_PRESENT")
    for snapshot in snapshots:
        for warning in snapshot.warnings:
            item = f"{snapshot.symbol}:{warning}"
            if item not in warnings:
                warnings.append(item)
    return warnings


def _monitor_status(summary: dict[str, Any], blockers: list[str]) -> QuoteFreshnessMonitorStatus:
    if summary["snapshot_count"] == 0:
        return QuoteFreshnessMonitorStatus.EMPTY
    if blockers:
        return QuoteFreshnessMonitorStatus.BLOCKED
    if summary["warning_count"]:
        return QuoteFreshnessMonitorStatus.DEGRADED
    return QuoteFreshnessMonitorStatus.HEALTHY

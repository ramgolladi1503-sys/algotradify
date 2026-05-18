from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


LIVE_MARKET_DATA_SNAPSHOT_SCHEMA_VERSION = "1.0"
DEFAULT_MAX_SPOT_QUOTE_AGE_SEC = 2.0
DEFAULT_MAX_OPTION_CHAIN_AGE_SEC = 5.0
FALLBACK_SOURCES = {"FALLBACK", "CACHE", "MOCK", "UNKNOWN"}
OPEN_SESSION_STATES = {"OPEN", "LIVE", "REGULAR"}


class LiveMarketDataSnapshotStatus(StrEnum):
    READY = "READY"
    BLOCKED_MISSING_SPOT = "BLOCKED_MISSING_SPOT"
    BLOCKED_STALE_SPOT = "BLOCKED_STALE_SPOT"
    BLOCKED_FALLBACK_SOURCE = "BLOCKED_FALLBACK_SOURCE"
    BLOCKED_MISSING_OPTION_CHAIN = "BLOCKED_MISSING_OPTION_CHAIN"
    BLOCKED_STALE_OPTION_CHAIN = "BLOCKED_STALE_OPTION_CHAIN"
    BLOCKED_SESSION_CLOSED = "BLOCKED_SESSION_CLOSED"


@dataclass(frozen=True)
class LiveMarketDataSnapshot:
    symbol: str
    status: LiveMarketDataSnapshotStatus
    spot: dict[str, Any]
    option_chain: dict[str, Any]
    source: str | None
    session_state: str | None
    spot_quote_fresh: bool
    option_chain_fresh: bool
    source_reliable: bool
    session_open: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = LIVE_MARKET_DATA_SNAPSHOT_SCHEMA_VERSION

    @property
    def read_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "snapshot_type": "LIVE_MARKET_DATA_SNAPSHOT",
            "symbol": self.symbol,
            "status": self.status.value,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "source": self.source,
            "session_state": self.session_state,
            "spot": dict(self.spot),
            "option_chain": dict(self.option_chain),
            "spot_quote_fresh": self.spot_quote_fresh,
            "option_chain_fresh": self.option_chain_fresh,
            "source_reliable": self.source_reliable,
            "session_open": self.session_open,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


def live_market_data_snapshot_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": LIVE_MARKET_DATA_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_type": "LIVE_MARKET_DATA_SNAPSHOT",
        "required_keys": [
            "schema_version",
            "snapshot_type",
            "symbol",
            "status",
            "read_only",
            "is_order_action",
            "source",
            "session_state",
            "spot",
            "option_chain",
            "spot_quote_fresh",
            "option_chain_fresh",
            "source_reliable",
            "session_open",
            "blockers",
            "warnings",
        ],
        "spot_required_keys": [
            "ltp",
            "quote_age_sec",
            "max_quote_age_sec",
        ],
        "option_chain_required_keys": [
            "age_sec",
            "max_age_sec",
            "expiry",
            "ce_count",
            "pe_count",
        ],
        "safe_flags": {"read_only": True, "is_order_action": False},
        "default_thresholds": {
            "max_spot_quote_age_sec": DEFAULT_MAX_SPOT_QUOTE_AGE_SEC,
            "max_option_chain_age_sec": DEFAULT_MAX_OPTION_CHAIN_AGE_SEC,
        },
    }


def build_live_market_data_snapshot(
    row: dict[str, Any] | None,
    *,
    max_spot_quote_age_sec: float = DEFAULT_MAX_SPOT_QUOTE_AGE_SEC,
    max_option_chain_age_sec: float = DEFAULT_MAX_OPTION_CHAIN_AGE_SEC,
) -> LiveMarketDataSnapshot:
    if not isinstance(row, dict):
        row = {}

    symbol = str(row.get("symbol") or row.get("underlying") or row.get("index_symbol") or "UNKNOWN").upper()
    source = _optional_text(row.get("source") or row.get("quote_source") or row.get("feed_source"))
    source_key = str(source or "UNKNOWN").upper()
    session_state = _optional_text(row.get("session_state") or row.get("market_session") or row.get("market_state"))
    session_key = str(session_state or "UNKNOWN").upper()
    spot_ltp = _num(row.get("spot_ltp") or row.get("spot_price") or row.get("ltp") or row.get("last_price"))
    spot_age = _num(row.get("spot_quote_age_sec") or row.get("quote_age_sec") or row.get("ltp_age_sec"))
    option_chain_age = _num(row.get("option_chain_age_sec") or row.get("chain_age_sec") or row.get("option_ltp_age_sec"))
    expiry = _optional_text(row.get("expiry") or row.get("expiry_context"))
    ce_count = _int(row.get("ce_count") or row.get("call_count") or row.get("option_ce_count"))
    pe_count = _int(row.get("pe_count") or row.get("put_count") or row.get("option_pe_count"))

    spot_quote_fresh = spot_ltp is not None and spot_age is not None and spot_age <= max_spot_quote_age_sec
    option_chain_present = option_chain_age is not None or ce_count is not None or pe_count is not None or expiry is not None
    option_chain_fresh = option_chain_age is not None and option_chain_age <= max_option_chain_age_sec
    source_reliable = bool(source_key) and source_key not in FALLBACK_SOURCES
    session_open = session_key in OPEN_SESSION_STATES

    blockers: list[str] = []
    warnings: list[str] = []

    if spot_ltp is None:
        blockers.append("MISSING_SPOT_LTP")
    if spot_age is None:
        blockers.append("MISSING_SPOT_QUOTE_AGE")
    elif spot_age > max_spot_quote_age_sec:
        blockers.append("STALE_SPOT_QUOTE")

    if not source_reliable:
        blockers.append("UNRELIABLE_MARKET_DATA_SOURCE")

    if not session_open:
        blockers.append("MARKET_SESSION_NOT_OPEN")

    if not option_chain_present:
        blockers.append("MISSING_OPTION_CHAIN")
    elif option_chain_age is None:
        blockers.append("MISSING_OPTION_CHAIN_AGE")
    elif option_chain_age > max_option_chain_age_sec:
        blockers.append("STALE_OPTION_CHAIN")

    if ce_count == 0 or pe_count == 0:
        warnings.append("OPTION_CHAIN_SIDE_COUNT_ZERO")
    if source is None:
        warnings.append("MARKET_DATA_SOURCE_MISSING")
    if session_state is None:
        warnings.append("MARKET_SESSION_STATE_MISSING")

    return LiveMarketDataSnapshot(
        symbol=symbol,
        status=_status_from_blockers(blockers),
        spot={
            "ltp": spot_ltp,
            "quote_age_sec": spot_age,
            "max_quote_age_sec": max_spot_quote_age_sec,
        },
        option_chain={
            "age_sec": option_chain_age,
            "max_age_sec": max_option_chain_age_sec,
            "expiry": expiry,
            "ce_count": ce_count,
            "pe_count": pe_count,
        },
        source=source,
        session_state=session_state,
        spot_quote_fresh=spot_quote_fresh,
        option_chain_fresh=option_chain_fresh,
        source_reliable=source_reliable,
        session_open=session_open,
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
    )


def _status_from_blockers(blockers: list[str]) -> LiveMarketDataSnapshotStatus:
    if "MISSING_SPOT_LTP" in blockers or "MISSING_SPOT_QUOTE_AGE" in blockers:
        return LiveMarketDataSnapshotStatus.BLOCKED_MISSING_SPOT
    if "STALE_SPOT_QUOTE" in blockers:
        return LiveMarketDataSnapshotStatus.BLOCKED_STALE_SPOT
    if "UNRELIABLE_MARKET_DATA_SOURCE" in blockers:
        return LiveMarketDataSnapshotStatus.BLOCKED_FALLBACK_SOURCE
    if "MISSING_OPTION_CHAIN" in blockers or "MISSING_OPTION_CHAIN_AGE" in blockers:
        return LiveMarketDataSnapshotStatus.BLOCKED_MISSING_OPTION_CHAIN
    if "STALE_OPTION_CHAIN" in blockers:
        return LiveMarketDataSnapshotStatus.BLOCKED_STALE_OPTION_CHAIN
    if "MARKET_SESSION_NOT_OPEN" in blockers:
        return LiveMarketDataSnapshotStatus.BLOCKED_SESSION_CLOSED
    return LiveMarketDataSnapshotStatus.READY


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


def _optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

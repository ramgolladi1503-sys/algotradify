from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any


MARKET_SESSION_EXPIRY_GUARD_SCHEMA_VERSION = "1.0"
DEFAULT_NEAR_EXPIRY_DAYS = 1
OPEN_SESSION_STATES = {"OPEN", "LIVE", "REGULAR"}
PRE_OPEN_SESSION_STATES = {"PRE_OPEN", "PREOPEN"}
CLOSING_SESSION_STATES = {"CLOSING", "CLOSE_AUCTION"}
CLOSED_SESSION_STATES = {"CLOSED", "HOLIDAY", "POST_CLOSE", "POSTCLOSE"}
SUPPORTED_EXPIRY_TYPES = {"WEEKLY", "MONTHLY", "UNKNOWN"}


class MarketSessionExpiryGuardStatus(StrEnum):
    READY = "READY"
    DEGRADED_NEAR_EXPIRY = "DEGRADED_NEAR_EXPIRY"
    BLOCKED_PRE_OPEN = "BLOCKED_PRE_OPEN"
    BLOCKED_CLOSING = "BLOCKED_CLOSING"
    BLOCKED_CLOSED = "BLOCKED_CLOSED"
    BLOCKED_EXPIRED_CONTRACT = "BLOCKED_EXPIRED_CONTRACT"
    BLOCKED_INVALID_EXPIRY = "BLOCKED_INVALID_EXPIRY"
    BLOCKED_MISSING_CONTEXT = "BLOCKED_MISSING_CONTEXT"


@dataclass(frozen=True)
class MarketSessionExpiryGuard:
    status: MarketSessionExpiryGuardStatus
    session_state: str | None
    expiry: str | None
    expiry_type: str
    trade_date: str | None
    days_to_expiry: int | None
    session_open: bool
    expiry_valid: bool
    contract_expired: bool
    near_expiry: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = MARKET_SESSION_EXPIRY_GUARD_SCHEMA_VERSION

    @property
    def read_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "guard_type": "MARKET_SESSION_EXPIRY_CONTEXT_GUARD",
            "status": self.status.value,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "session_state": self.session_state,
            "expiry": self.expiry,
            "expiry_type": self.expiry_type,
            "trade_date": self.trade_date,
            "days_to_expiry": self.days_to_expiry,
            "session_open": self.session_open,
            "expiry_valid": self.expiry_valid,
            "contract_expired": self.contract_expired,
            "near_expiry": self.near_expiry,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


def market_session_expiry_guard_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": MARKET_SESSION_EXPIRY_GUARD_SCHEMA_VERSION,
        "guard_type": "MARKET_SESSION_EXPIRY_CONTEXT_GUARD",
        "required_keys": [
            "schema_version",
            "guard_type",
            "status",
            "read_only",
            "is_order_action",
            "session_state",
            "expiry",
            "expiry_type",
            "trade_date",
            "days_to_expiry",
            "session_open",
            "expiry_valid",
            "contract_expired",
            "near_expiry",
            "blockers",
            "warnings",
        ],
        "safe_flags": {"read_only": True, "is_order_action": False},
        "open_session_states": sorted(OPEN_SESSION_STATES),
        "supported_expiry_types": sorted(SUPPORTED_EXPIRY_TYPES),
        "default_thresholds": {"near_expiry_days": DEFAULT_NEAR_EXPIRY_DAYS},
    }


def build_market_session_expiry_guard(
    row: dict[str, Any] | None,
    *,
    today: date | datetime | str | None = None,
    near_expiry_days: int = DEFAULT_NEAR_EXPIRY_DAYS,
) -> MarketSessionExpiryGuard:
    if not isinstance(row, dict):
        row = {}

    trade_day = _coerce_date(today) or _coerce_date(_first_present(row, "trade_date", "asof_date", "today")) or datetime.now(timezone.utc).date()
    session_state = _optional_text(_first_present(row, "session_state", "market_session", "market_state"))
    session_key = str(session_state or "").upper()
    expiry_raw = _optional_text(_first_present(row, "expiry", "expiry_date", "contract_expiry"))
    expiry_date = _coerce_date(expiry_raw)
    expiry_type = str(_first_present(row, "expiry_type", "expiry_context", default="UNKNOWN") or "UNKNOWN").upper()
    if expiry_type not in SUPPORTED_EXPIRY_TYPES:
        expiry_type = "UNKNOWN"

    blockers: list[str] = []
    warnings: list[str] = []

    if not session_state:
        blockers.append("MISSING_MARKET_SESSION_STATE")
    elif session_key in PRE_OPEN_SESSION_STATES:
        blockers.append("MARKET_SESSION_PRE_OPEN")
    elif session_key in CLOSING_SESSION_STATES:
        blockers.append("MARKET_SESSION_CLOSING")
    elif session_key in CLOSED_SESSION_STATES:
        blockers.append("MARKET_SESSION_CLOSED")
    elif session_key not in OPEN_SESSION_STATES:
        blockers.append("UNKNOWN_MARKET_SESSION_STATE")

    if not expiry_raw:
        blockers.append("MISSING_EXPIRY")
    elif expiry_date is None:
        blockers.append("INVALID_EXPIRY")

    days_to_expiry = (expiry_date - trade_day).days if expiry_date else None
    contract_expired = days_to_expiry is not None and days_to_expiry < 0
    near_expiry = days_to_expiry is not None and 0 <= days_to_expiry <= near_expiry_days
    expiry_valid = expiry_date is not None and not contract_expired

    if contract_expired:
        blockers.append("EXPIRED_CONTRACT")
    if near_expiry:
        warnings.append("NEAR_EXPIRY_CONTRACT")
    if expiry_type == "UNKNOWN":
        warnings.append("EXPIRY_TYPE_UNKNOWN")

    return MarketSessionExpiryGuard(
        status=_status_from_context(blockers, warnings),
        session_state=session_state,
        expiry=expiry_raw,
        expiry_type=expiry_type,
        trade_date=trade_day.isoformat(),
        days_to_expiry=days_to_expiry,
        session_open=session_key in OPEN_SESSION_STATES,
        expiry_valid=expiry_valid,
        contract_expired=contract_expired,
        near_expiry=near_expiry,
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
    )


def _status_from_context(blockers: list[str], warnings: list[str]) -> MarketSessionExpiryGuardStatus:
    if "MISSING_MARKET_SESSION_STATE" in blockers or "MISSING_EXPIRY" in blockers:
        return MarketSessionExpiryGuardStatus.BLOCKED_MISSING_CONTEXT
    if "MARKET_SESSION_PRE_OPEN" in blockers:
        return MarketSessionExpiryGuardStatus.BLOCKED_PRE_OPEN
    if "MARKET_SESSION_CLOSING" in blockers:
        return MarketSessionExpiryGuardStatus.BLOCKED_CLOSING
    if "MARKET_SESSION_CLOSED" in blockers or "UNKNOWN_MARKET_SESSION_STATE" in blockers:
        return MarketSessionExpiryGuardStatus.BLOCKED_CLOSED
    if "INVALID_EXPIRY" in blockers:
        return MarketSessionExpiryGuardStatus.BLOCKED_INVALID_EXPIRY
    if "EXPIRED_CONTRACT" in blockers:
        return MarketSessionExpiryGuardStatus.BLOCKED_EXPIRED_CONTRACT
    if "NEAR_EXPIRY_CONTRACT" in warnings:
        return MarketSessionExpiryGuardStatus.DEGRADED_NEAR_EXPIRY
    return MarketSessionExpiryGuardStatus.READY


def _first_present(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _coerce_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
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

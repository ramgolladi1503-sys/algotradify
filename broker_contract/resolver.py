from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BrokerContractResolutionStatus(StrEnum):
    EXACT = "EXACT"
    FALLBACK = "FALLBACK"
    NOT_FOUND = "NOT_FOUND"
    COVERAGE_FAILED = "COVERAGE_FAILED"
    INVALID_REQUEST = "INVALID_REQUEST"


class TokenCoverageError(RuntimeError):
    """Raised when the instrument universe is too small to trust resolution."""


@dataclass(frozen=True)
class OptionContractRequest:
    symbol: str
    expiry: str
    strike: float | int
    option_type: str
    exchange: str = "NFO"

    def normalized(self) -> "OptionContractRequest":
        return OptionContractRequest(
            symbol=self.symbol.upper().strip(),
            expiry=str(self.expiry).strip(),
            strike=float(self.strike),
            option_type=self.option_type.upper().strip(),
            exchange=self.exchange.upper().strip(),
        )


@dataclass(frozen=True)
class BrokerContractResolution:
    status: BrokerContractResolutionStatus
    resolved: bool
    request: dict[str, Any]
    instrument: dict[str, Any] | None = None
    fallback_used: bool = False
    fallback_distance: float | None = None
    reason: str | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def instrument_token(self) -> Any | None:
        return self.instrument.get("instrument_token") if self.instrument else None

    @property
    def is_execution_decision(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "resolved": self.resolved,
            "request": dict(self.request),
            "instrument": dict(self.instrument) if self.instrument else None,
            "instrument_token": self.instrument_token,
            "fallback_used": self.fallback_used,
            "fallback_distance": self.fallback_distance,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "is_execution_decision": self.is_execution_decision,
        }


def _request_dict(request: OptionContractRequest) -> dict[str, Any]:
    normalized = request.normalized()
    return {
        "symbol": normalized.symbol,
        "expiry": normalized.expiry,
        "strike": normalized.strike,
        "option_type": normalized.option_type,
        "exchange": normalized.exchange,
    }


def _instrument_symbol(row: dict[str, Any]) -> str:
    return str(row.get("symbol") or row.get("name") or row.get("underlying") or "").upper().strip()


def _instrument_expiry(row: dict[str, Any]) -> str:
    return str(row.get("expiry") or row.get("expiry_date") or "").strip()


def _instrument_type(row: dict[str, Any]) -> str:
    raw = row.get("instrument_type") or row.get("option_type") or row.get("type") or ""
    return str(raw).upper().strip()


def _instrument_exchange(row: dict[str, Any]) -> str:
    return str(row.get("exchange") or "NFO").upper().strip()


def _instrument_strike(row: dict[str, Any]) -> float | None:
    try:
        return float(row.get("strike"))
    except (TypeError, ValueError):
        return None


def _has_token(row: dict[str, Any]) -> bool:
    return row.get("instrument_token") not in (None, "")


def _same_contract_family(row: dict[str, Any], request: OptionContractRequest) -> bool:
    normalized = request.normalized()
    return (
        _instrument_symbol(row) == normalized.symbol
        and _instrument_expiry(row) == normalized.expiry
        and _instrument_type(row) == normalized.option_type
        and _instrument_exchange(row) == normalized.exchange
    )


def _find_exact(instruments: list[dict[str, Any]], request: OptionContractRequest) -> dict[str, Any] | None:
    normalized = request.normalized()
    for row in instruments:
        strike = _instrument_strike(row)
        if strike is None:
            continue
        if _same_contract_family(row, normalized) and strike == normalized.strike and _has_token(row):
            return row
    return None


def _find_safe_fallback(
    instruments: list[dict[str, Any]],
    request: OptionContractRequest,
    *,
    max_fallback_distance: float,
) -> tuple[dict[str, Any] | None, float | None]:
    normalized = request.normalized()
    candidates: list[tuple[float, dict[str, Any]]] = []
    for row in instruments:
        if not _same_contract_family(row, normalized) or not _has_token(row):
            continue
        strike = _instrument_strike(row)
        if strike is None:
            continue
        distance = abs(float(strike) - normalized.strike)
        if distance <= max_fallback_distance:
            candidates.append((distance, row))
    if not candidates:
        return None, None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1], candidates[0][0]


def _coverage_count(instruments: list[dict[str, Any]], request: OptionContractRequest) -> int:
    normalized = request.normalized()
    return sum(1 for row in instruments if _same_contract_family(row, normalized) and _has_token(row))


def _valid_request(request: OptionContractRequest) -> bool:
    normalized = request.normalized()
    return bool(normalized.symbol and normalized.expiry and normalized.option_type in {"CE", "PE"} and normalized.strike > 0)


def resolve_option_contract(
    request: OptionContractRequest,
    instruments: list[dict[str, Any]],
    *,
    allow_fallback: bool = True,
    max_fallback_distance: float = 100.0,
    min_token_coverage: int = 1,
) -> BrokerContractResolution:
    """Resolve an option contract safely.

    Contract resolution failure must be explicit. No exact/no fallback returns a
    NOT_FOUND resolution instead of raising `AttributeError` or pretending a
    fallback exists.
    """
    normalized = request.normalized()
    request_payload = _request_dict(normalized)

    if not _valid_request(normalized):
        return BrokerContractResolution(
            status=BrokerContractResolutionStatus.INVALID_REQUEST,
            resolved=False,
            request=request_payload,
            reason="INVALID_OPTION_CONTRACT_REQUEST",
            blockers=["INVALID_OPTION_CONTRACT_REQUEST"],
        )

    coverage = _coverage_count(instruments, normalized)
    if coverage < min_token_coverage:
        raise TokenCoverageError(
            f"Token coverage below threshold for {normalized.symbol} {normalized.expiry} "
            f"{normalized.option_type}: coverage={coverage}, required={min_token_coverage}"
        )

    exact = _find_exact(instruments, normalized)
    if exact is not None:
        return BrokerContractResolution(
            status=BrokerContractResolutionStatus.EXACT,
            resolved=True,
            request=request_payload,
            instrument=exact,
            fallback_used=False,
            reason="EXACT_CONTRACT_MATCH",
        )

    fallback: dict[str, Any] | None = None
    fallback_distance: float | None = None
    if allow_fallback:
        fallback, fallback_distance = _find_safe_fallback(
            instruments,
            normalized,
            max_fallback_distance=max_fallback_distance,
        )

    if fallback is not None:
        return BrokerContractResolution(
            status=BrokerContractResolutionStatus.FALLBACK,
            resolved=True,
            request=request_payload,
            instrument=fallback,
            fallback_used=True,
            fallback_distance=fallback_distance,
            reason="SAFE_FALLBACK_CONTRACT_MATCH",
            warnings=["FALLBACK_CONTRACT_USED"],
        )

    return BrokerContractResolution(
        status=BrokerContractResolutionStatus.NOT_FOUND,
        resolved=False,
        request=request_payload,
        instrument=None,
        fallback_used=False,
        fallback_distance=None,
        reason="OPTION_TOKEN_NOT_FOUND",
        blockers=["OPTION_TOKEN_NOT_FOUND"],
    )

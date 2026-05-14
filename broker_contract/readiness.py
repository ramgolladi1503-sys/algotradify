from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from broker_contract.resolver import (
    BrokerContractResolution,
    BrokerContractResolutionStatus,
    OptionContractRequest,
    TokenCoverageError,
    resolve_option_contract,
)
from candidate_truth import CandidateTruthRecord, normalize_candidate, normalize_candidates


class BrokerContractReadinessStatus(StrEnum):
    RESOLVED_EXACT = "RESOLVED_EXACT"
    RESOLVED_FALLBACK = "RESOLVED_FALLBACK"
    BLOCKED_NOT_FOUND = "BLOCKED_NOT_FOUND"
    BLOCKED_COVERAGE_FAILED = "BLOCKED_COVERAGE_FAILED"
    BLOCKED_INVALID_REQUEST = "BLOCKED_INVALID_REQUEST"
    BLOCKED_MISSING_REQUEST = "BLOCKED_MISSING_REQUEST"


_REQUIRED_REQUEST_FIELDS = ("expiry", "strike", "option_type")


@dataclass(frozen=True)
class BrokerContractReadiness:
    candidate_id: str
    symbol: str | None
    strategy_id: str | None
    setup_family: str | None
    readiness_status: BrokerContractReadinessStatus
    resolved: bool
    request: dict[str, Any]
    resolution: dict[str, Any] | None = None
    instrument_token: Any | None = None
    fallback_used: bool = False
    fallback_distance: float | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    candidate_truth: dict[str, Any] = field(default_factory=dict)

    @property
    def is_execution_decision(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "strategy_id": self.strategy_id,
            "setup_family": self.setup_family,
            "readiness_status": self.readiness_status.value,
            "resolved": self.resolved,
            "request": dict(self.request),
            "resolution": dict(self.resolution) if self.resolution else None,
            "instrument_token": self.instrument_token,
            "fallback_used": self.fallback_used,
            "fallback_distance": self.fallback_distance,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "candidate_truth": dict(self.candidate_truth),
            "is_execution_decision": self.is_execution_decision,
        }


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _extract_request_payload(record: CandidateTruthRecord) -> dict[str, Any]:
    normalized = record.normalized or {}
    raw = record.raw or {}
    raw_payload = raw.get("raw") if isinstance(raw.get("raw"), dict) else {}
    entry_hypothesis = normalized.get("entry_hypothesis") or raw.get("entry_hypothesis") or {}
    if not isinstance(entry_hypothesis, dict):
        entry_hypothesis = {}

    symbol = _first_present(
        normalized.get("symbol"),
        record.symbol,
        raw.get("symbol"),
        raw.get("underlying"),
        raw_payload.get("symbol"),
        raw_payload.get("underlying"),
    )
    expiry = _first_present(
        normalized.get("expiry"),
        raw.get("expiry"),
        raw.get("expiry_date"),
        raw_payload.get("expiry"),
        raw_payload.get("expiry_date"),
        entry_hypothesis.get("expiry"),
    )
    strike = _first_present(
        normalized.get("strike"),
        raw.get("strike"),
        raw.get("option_strike"),
        raw_payload.get("strike"),
        raw_payload.get("option_strike"),
        entry_hypothesis.get("strike"),
    )
    option_type = _first_present(
        normalized.get("option_type"),
        raw.get("option_type"),
        raw.get("instrument_type"),
        raw_payload.get("option_type"),
        raw_payload.get("instrument_type"),
        entry_hypothesis.get("option_type"),
    )
    exchange = _first_present(
        normalized.get("exchange"),
        raw.get("exchange"),
        raw_payload.get("exchange"),
        entry_hypothesis.get("exchange"),
        "NFO",
    )

    return {
        "symbol": str(symbol).upper().strip() if symbol is not None else None,
        "expiry": str(expiry).strip() if expiry is not None else None,
        "strike": strike,
        "option_type": str(option_type).upper().strip() if option_type is not None else None,
        "exchange": str(exchange).upper().strip() if exchange is not None else "NFO",
    }


def _missing_request_fields(payload: dict[str, Any]) -> list[str]:
    missing = []
    for field_name in _REQUIRED_REQUEST_FIELDS:
        if payload.get(field_name) in (None, ""):
            missing.append(f"MISSING_CONTRACT_{field_name.upper()}")
    if payload.get("symbol") in (None, ""):
        missing.append("MISSING_CONTRACT_SYMBOL")
    return missing


def _readiness_status_from_resolution(resolution: BrokerContractResolution) -> BrokerContractReadinessStatus:
    if resolution.status == BrokerContractResolutionStatus.EXACT:
        return BrokerContractReadinessStatus.RESOLVED_EXACT
    if resolution.status == BrokerContractResolutionStatus.FALLBACK:
        return BrokerContractReadinessStatus.RESOLVED_FALLBACK
    if resolution.status == BrokerContractResolutionStatus.INVALID_REQUEST:
        return BrokerContractReadinessStatus.BLOCKED_INVALID_REQUEST
    if resolution.status == BrokerContractResolutionStatus.NOT_FOUND:
        return BrokerContractReadinessStatus.BLOCKED_NOT_FOUND
    return BrokerContractReadinessStatus.BLOCKED_COVERAGE_FAILED


def build_broker_contract_readiness(
    candidate: Any,
    instruments: list[dict[str, Any]],
    *,
    source: str = "unknown",
    allow_fallback: bool = True,
    max_fallback_distance: float = 100.0,
    min_token_coverage: int = 1,
) -> BrokerContractReadiness:
    record = candidate if isinstance(candidate, CandidateTruthRecord) else normalize_candidate(candidate, source=source)
    request_payload = _extract_request_payload(record)
    missing = _missing_request_fields(request_payload)
    candidate_truth = record.to_dict()

    if missing:
        return BrokerContractReadiness(
            candidate_id=record.candidate_id,
            symbol=record.symbol,
            strategy_id=record.strategy_id,
            setup_family=record.setup_family,
            readiness_status=BrokerContractReadinessStatus.BLOCKED_MISSING_REQUEST,
            resolved=False,
            request=request_payload,
            blockers=missing,
            warnings=list(record.warnings),
            candidate_truth=candidate_truth,
        )

    try:
        request = OptionContractRequest(
            symbol=str(request_payload["symbol"]),
            expiry=str(request_payload["expiry"]),
            strike=float(request_payload["strike"]),
            option_type=str(request_payload["option_type"]),
            exchange=str(request_payload.get("exchange") or "NFO"),
        )
        resolution = resolve_option_contract(
            request,
            instruments,
            allow_fallback=allow_fallback,
            max_fallback_distance=max_fallback_distance,
            min_token_coverage=min_token_coverage,
        )
    except TokenCoverageError as exc:
        return BrokerContractReadiness(
            candidate_id=record.candidate_id,
            symbol=record.symbol,
            strategy_id=record.strategy_id,
            setup_family=record.setup_family,
            readiness_status=BrokerContractReadinessStatus.BLOCKED_COVERAGE_FAILED,
            resolved=False,
            request=request_payload,
            blockers=["TOKEN_COVERAGE_BELOW_THRESHOLD"],
            warnings=list(record.warnings),
            candidate_truth=candidate_truth,
            resolution={"error": str(exc)},
        )

    resolution_payload = resolution.to_dict()
    blockers = list(record.blockers) + list(resolution.blockers)
    warnings = list(record.warnings) + list(resolution.warnings)

    return BrokerContractReadiness(
        candidate_id=record.candidate_id,
        symbol=record.symbol,
        strategy_id=record.strategy_id,
        setup_family=record.setup_family,
        readiness_status=_readiness_status_from_resolution(resolution),
        resolved=resolution.resolved,
        request=request_payload,
        resolution=resolution_payload,
        instrument_token=resolution.instrument_token,
        fallback_used=resolution.fallback_used,
        fallback_distance=resolution.fallback_distance,
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
        candidate_truth=candidate_truth,
    )


def build_broker_contract_readiness_batch(
    candidates: list[Any],
    instruments: list[dict[str, Any]],
    *,
    source: str = "unknown",
    allow_fallback: bool = True,
    max_fallback_distance: float = 100.0,
    min_token_coverage: int = 1,
) -> list[BrokerContractReadiness]:
    records = normalize_candidates(candidates, source=source)
    return [
        build_broker_contract_readiness(
            record,
            instruments,
            source=source,
            allow_fallback=allow_fallback,
            max_fallback_distance=max_fallback_distance,
            min_token_coverage=min_token_coverage,
        )
        for record in records
    ]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

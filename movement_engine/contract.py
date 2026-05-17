from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


MOVEMENT_CANDIDATE_SCHEMA_VERSION = 1


class Direction(StrEnum):
    BUY_CALL = "BUY_CALL"
    BUY_PUT = "BUY_PUT"
    NO_TRADE = "NO_TRADE"


class CandidateStatus(StrEnum):
    RAW_CANDIDATE = "RAW_CANDIDATE"
    VALIDATED_CANDIDATE = "VALIDATED_CANDIDATE"
    BLOCKED_CANDIDATE = "BLOCKED_CANDIDATE"
    RANKED_OPPORTUNITY = "RANKED_OPPORTUNITY"
    NO_TRADE = "NO_TRADE"


SCORE_FIELDS = (
    "raw_score",
    "confidence_score",
    "price_structure_score",
    "option_confirmation_score",
    "liquidity_score",
    "freshness_score",
    "volatility_score",
    "regime_alignment_score",
)


@dataclass(frozen=True)
class StrategyCandidate:
    schema_version: int
    candidate_id: str
    strategy_id: str
    movement_type: str
    symbol: str
    direction: Direction
    status: CandidateStatus
    raw_score: float
    confidence_score: float
    price_structure_score: float
    option_confirmation_score: float
    liquidity_score: float
    freshness_score: float
    volatility_score: float
    regime_alignment_score: float
    entry_trigger: str
    invalid_if: str
    rank_reason: str
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "movement_type": self.movement_type,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "status": self.status.value,
            "raw_score": self.raw_score,
            "confidence_score": self.confidence_score,
            "price_structure_score": self.price_structure_score,
            "option_confirmation_score": self.option_confirmation_score,
            "liquidity_score": self.liquidity_score,
            "freshness_score": self.freshness_score,
            "volatility_score": self.volatility_score,
            "regime_alignment_score": self.regime_alignment_score,
            "entry_trigger": self.entry_trigger,
            "invalid_if": self.invalid_if,
            "rank_reason": self.rank_reason,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class MovementCandidateValidationResult:
    valid: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "is_order_action": self.is_order_action,
        }


def validate_strategy_candidate(candidate: StrategyCandidate | Mapping[str, Any] | None) -> MovementCandidateValidationResult:
    if candidate is None:
        return MovementCandidateValidationResult(valid=False, blockers=["CANDIDATE_REQUIRED"])

    payload = candidate.to_dict() if isinstance(candidate, StrategyCandidate) else dict(candidate)
    blockers: list[str] = []
    warnings: list[str] = []

    if payload.get("schema_version") != MOVEMENT_CANDIDATE_SCHEMA_VERSION:
        blockers.append("INVALID_SCHEMA_VERSION")

    for field_name in ("candidate_id", "strategy_id", "movement_type", "symbol", "entry_trigger", "invalid_if", "rank_reason"):
        if _blank(payload.get(field_name)):
            blockers.append(f"{field_name.upper()}_REQUIRED")

    if _enum_value(payload.get("direction"), Direction) is None:
        blockers.append("INVALID_DIRECTION")

    status = _enum_value(payload.get("status"), CandidateStatus)
    if status is None:
        blockers.append("INVALID_STATUS")

    for field_name in SCORE_FIELDS:
        score = _float_or_none(payload.get(field_name))
        if score is None:
            blockers.append(f"{field_name.upper()}_REQUIRED")
        elif score < 0.0 or score > 1.0:
            blockers.append(f"{field_name.upper()}_OUT_OF_RANGE")

    blockers_value = payload.get("blockers", [])
    warnings_value = payload.get("warnings", [])
    if not _is_string_sequence(blockers_value):
        blockers.append("BLOCKERS_MUST_BE_STRING_LIST")
    if not _is_string_sequence(warnings_value):
        blockers.append("WARNINGS_MUST_BE_STRING_LIST")

    if not isinstance(payload.get("evidence", {}), dict):
        blockers.append("EVIDENCE_MUST_BE_DICT")

    if payload.get("is_order_action") is not False:
        blockers.append("CANDIDATE_ORDER_FLAG_UNSAFE")

    if status == CandidateStatus.NO_TRADE and payload.get("direction") != Direction.NO_TRADE.value:
        blockers.append("NO_TRADE_STATUS_REQUIRES_NO_TRADE_DIRECTION")

    if status in {CandidateStatus.BLOCKED_CANDIDATE, CandidateStatus.NO_TRADE} and _is_empty_sequence(blockers_value):
        warnings.append("BLOCKED_OR_NO_TRADE_WITHOUT_EXPLANATORY_BLOCKER")

    return MovementCandidateValidationResult(valid=not blockers, blockers=_dedupe(blockers), warnings=_dedupe(warnings))


def candidate_from_mapping(payload: Mapping[str, Any]) -> StrategyCandidate:
    return StrategyCandidate(
        schema_version=int(payload.get("schema_version", MOVEMENT_CANDIDATE_SCHEMA_VERSION)),
        candidate_id=str(payload.get("candidate_id", "")),
        strategy_id=str(payload.get("strategy_id", "")),
        movement_type=str(payload.get("movement_type", "")),
        symbol=str(payload.get("symbol", "")),
        direction=Direction(str(payload.get("direction", ""))),
        status=CandidateStatus(str(payload.get("status", ""))),
        raw_score=float(payload.get("raw_score", 0.0)),
        confidence_score=float(payload.get("confidence_score", 0.0)),
        price_structure_score=float(payload.get("price_structure_score", 0.0)),
        option_confirmation_score=float(payload.get("option_confirmation_score", 0.0)),
        liquidity_score=float(payload.get("liquidity_score", 0.0)),
        freshness_score=float(payload.get("freshness_score", 0.0)),
        volatility_score=float(payload.get("volatility_score", 0.0)),
        regime_alignment_score=float(payload.get("regime_alignment_score", 0.0)),
        entry_trigger=str(payload.get("entry_trigger", "")),
        invalid_if=str(payload.get("invalid_if", "")),
        rank_reason=str(payload.get("rank_reason", "")),
        blockers=tuple(str(item) for item in payload.get("blockers", ())),
        warnings=tuple(str(item) for item in payload.get("warnings", ())),
        evidence=dict(payload.get("evidence", {})),
    )


def _enum_value(value: Any, enum_cls: type[StrEnum]) -> StrEnum | None:
    try:
        return enum_cls(str(value))
    except Exception:
        return None


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_string_sequence(value: Any) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    return all(isinstance(item, str) and item.strip() for item in value)


def _is_empty_sequence(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 0


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out

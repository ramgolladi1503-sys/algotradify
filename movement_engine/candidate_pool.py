from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from movement_engine.contract import (
    MOVEMENT_CANDIDATE_SCHEMA_VERSION,
    CandidateStatus,
    Direction,
    StrategyCandidate,
    candidate_from_mapping,
    validate_strategy_candidate,
)


HARD_POOL_BLOCKERS = (
    "STALE_OPTION_LTP",
    "WIDE_SPREAD",
    "MISSING_DEPTH",
    "FALLBACK_QUOTE_ONLY",
    "UNRESOLVED_CONTRACT",
    "CONFLICTING_TRAP_SIGNAL",
    "NO_TRADE_CHOP",
    "MARKET_CLOSED",
    "EXECUTION_SAFETY_NOT_PERMITTED",
)

EXECUTABLE_LIKE_STATUSES = (
    CandidateStatus.VALIDATED_CANDIDATE,
    CandidateStatus.RANKED_OPPORTUNITY,
)


@dataclass(frozen=True)
class CandidatePoolSummary:
    input_count: int = 0
    candidate_count: int = 0
    raw_count: int = 0
    valid_count: int = 0
    blocked_count: int = 0
    no_trade_count: int = 0

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_count": self.input_count,
            "candidate_count": self.candidate_count,
            "raw_count": self.raw_count,
            "valid_count": self.valid_count,
            "blocked_count": self.blocked_count,
            "no_trade_count": self.no_trade_count,
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class CandidatePoolResult:
    candidates: tuple[StrategyCandidate, ...] = ()
    summary: CandidatePoolSummary = field(default_factory=CandidatePoolSummary)
    warnings: tuple[str, ...] = ()
    diagnostics: tuple[dict[str, Any], ...] = ()

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "summary": self.summary.to_dict(),
            "warnings": list(self.warnings),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "is_order_action": self.is_order_action,
        }


RawPoolCandidate = StrategyCandidate | Mapping[str, Any] | Any


def build_candidate_pool(
    candidates: Iterable[RawPoolCandidate] | None,
    *,
    upstream_warnings: Iterable[str] = (),
    upstream_diagnostics: Iterable[Mapping[str, Any]] = (),
) -> CandidatePoolResult:
    """Validate, hard-block, and dedupe raw movement candidates.

    This function is still a pool shell. It does not rank, execute, call a
    broker, or infer trades. It only turns provider output into a stable,
    read-only candidate pool.
    """

    raw_items = _normalize_pool_input(candidates)
    warnings: list[str] = list(upstream_warnings)
    diagnostics: list[dict[str, Any]] = [dict(item) for item in upstream_diagnostics]
    normalized: list[StrategyCandidate] = []

    for index, item in enumerate(raw_items):
        candidate, item_diagnostics, item_warnings = _coerce_candidate(item, index)
        diagnostics.extend(item_diagnostics)
        warnings.extend(item_warnings)
        normalized.append(_apply_hard_blockers(candidate))

    deduped, dedupe_diagnostics, dedupe_warnings = _dedupe_candidates(normalized)
    diagnostics.extend(dedupe_diagnostics)
    warnings.extend(dedupe_warnings)

    final_candidates = tuple(deduped)
    return CandidatePoolResult(
        candidates=final_candidates,
        summary=_summarize(raw_items, final_candidates),
        warnings=tuple(_dedupe(warnings)),
        diagnostics=tuple(diagnostics),
    )


def _normalize_pool_input(candidates: Iterable[RawPoolCandidate] | None) -> list[RawPoolCandidate]:
    if candidates is None:
        return []
    if isinstance(candidates, (StrategyCandidate, Mapping)):
        return [candidates]
    if isinstance(candidates, (str, bytes)):
        return [candidates]
    return list(candidates)


def _coerce_candidate(
    item: RawPoolCandidate,
    index: int,
) -> tuple[StrategyCandidate, list[dict[str, Any]], list[str]]:
    if isinstance(item, StrategyCandidate):
        validation = validate_strategy_candidate(item)
        if validation.valid:
            return item, [], list(validation.warnings)
        return (
            _blocked_candidate_from_invalid(item.to_dict(), validation.blockers, validation.warnings, index),
            [
                _diagnostic(
                    code="INVALID_CANDIDATE_CONTRACT",
                    candidate_id=item.candidate_id,
                    message="StrategyCandidate failed movement candidate validation.",
                    blockers=validation.blockers,
                )
            ],
            ["INVALID_CANDIDATE_CONTRACT"],
        )

    if isinstance(item, Mapping):
        payload = dict(item)
        validation = validate_strategy_candidate(payload)
        if validation.valid:
            return candidate_from_mapping(payload), [], list(validation.warnings)
        return (
            _blocked_candidate_from_invalid(payload, validation.blockers, validation.warnings, index),
            [
                _diagnostic(
                    code="INVALID_CANDIDATE_CONTRACT",
                    candidate_id=str(payload.get("candidate_id") or f"invalid-candidate-{index + 1}"),
                    message="Provider mapping failed movement candidate validation.",
                    blockers=validation.blockers,
                )
            ],
            ["INVALID_CANDIDATE_CONTRACT"],
        )

    return (
        _blocked_candidate_from_invalid(
            {},
            ["INVALID_PROVIDER_OUTPUT"],
            [],
            index,
            item_type=type(item).__name__,
        ),
        [
            _diagnostic(
                code="INVALID_PROVIDER_OUTPUT",
                candidate_id=f"invalid-candidate-{index + 1}",
                message="Candidate pool received non-candidate provider output.",
                blockers=["INVALID_PROVIDER_OUTPUT"],
                item_type=type(item).__name__,
            )
        ],
        ["INVALID_PROVIDER_OUTPUT"],
    )


def _blocked_candidate_from_invalid(
    payload: Mapping[str, Any],
    blockers: list[str],
    warnings: list[str],
    index: int,
    **extra_evidence: Any,
) -> StrategyCandidate:
    payload_dict = dict(payload)
    supplied_evidence = payload_dict.get("evidence", {})
    evidence = dict(supplied_evidence) if isinstance(supplied_evidence, dict) else {}
    evidence.update(
        {
            "pool_validation_blockers": list(blockers),
            "invalid_provider_payload": _safe_payload(payload_dict),
            **extra_evidence,
        }
    )

    return StrategyCandidate(
        schema_version=MOVEMENT_CANDIDATE_SCHEMA_VERSION,
        candidate_id=str(payload_dict.get("candidate_id") or f"invalid-candidate-{index + 1}"),
        strategy_id=str(payload_dict.get("strategy_id") or "UNKNOWN_PROVIDER"),
        movement_type=str(payload_dict.get("movement_type") or "INVALID_PROVIDER_OUTPUT"),
        symbol=str(payload_dict.get("symbol") or "UNKNOWN"),
        direction=Direction.NO_TRADE,
        status=CandidateStatus.BLOCKED_CANDIDATE,
        raw_score=0.0,
        confidence_score=0.0,
        price_structure_score=0.0,
        option_confirmation_score=0.0,
        liquidity_score=0.0,
        freshness_score=0.0,
        volatility_score=0.0,
        regime_alignment_score=0.0,
        entry_trigger="blocked before candidate pool admission",
        invalid_if="candidate failed movement candidate contract validation",
        rank_reason="candidate pool blocked invalid provider output",
        blockers=tuple(_dedupe(blockers or ["INVALID_PROVIDER_OUTPUT"])),
        warnings=tuple(_dedupe(warnings)),
        evidence=evidence,
    )


def _apply_hard_blockers(candidate: StrategyCandidate) -> StrategyCandidate:
    hard_blockers = tuple(blocker for blocker in candidate.blockers if blocker in HARD_POOL_BLOCKERS)
    if not hard_blockers:
        return candidate

    evidence = dict(candidate.evidence)
    evidence["pool_hard_blockers"] = list(hard_blockers)
    evidence["pool_blocked"] = True

    if candidate.status == CandidateStatus.NO_TRADE:
        return replace(
            candidate,
            blockers=tuple(_dedupe(list(candidate.blockers))),
            warnings=tuple(_dedupe(list(candidate.warnings) + ["POOL_HARD_BLOCKER_APPLIED"])),
            evidence=evidence,
        )

    return replace(
        candidate,
        status=CandidateStatus.BLOCKED_CANDIDATE,
        blockers=tuple(_dedupe(list(candidate.blockers))),
        warnings=tuple(_dedupe(list(candidate.warnings) + ["POOL_HARD_BLOCKER_APPLIED"])),
        evidence=evidence,
    )


def _dedupe_candidates(
    candidates: list[StrategyCandidate],
) -> tuple[list[StrategyCandidate], list[dict[str, Any]], list[str]]:
    by_candidate_id: dict[str, StrategyCandidate] = {}
    diagnostics: list[dict[str, Any]] = []
    warnings: list[str] = []

    for candidate in candidates:
        existing = by_candidate_id.get(candidate.candidate_id)
        if existing is None:
            by_candidate_id[candidate.candidate_id] = candidate
            continue

        selected, dropped = _select_candidate(existing, candidate)
        by_candidate_id[candidate.candidate_id] = selected
        warnings.append("DUPLICATE_CANDIDATE_DEDUPED")
        diagnostics.append(
            _diagnostic(
                code="DUPLICATE_CANDIDATE_DEDUPED",
                candidate_id=candidate.candidate_id,
                message="Duplicate candidate_id collapsed deterministically.",
                kept_strategy_id=selected.strategy_id,
                dropped_strategy_id=dropped.strategy_id,
            )
        )

    return [by_candidate_id[key] for key in sorted(by_candidate_id)], diagnostics, warnings


def _select_candidate(
    left: StrategyCandidate,
    right: StrategyCandidate,
) -> tuple[StrategyCandidate, StrategyCandidate]:
    if _candidate_preference_key(right) < _candidate_preference_key(left):
        return right, left
    return left, right


def _candidate_preference_key(candidate: StrategyCandidate) -> tuple[int, float, str, str, str]:
    status_rank = {
        CandidateStatus.RANKED_OPPORTUNITY: 0,
        CandidateStatus.VALIDATED_CANDIDATE: 1,
        CandidateStatus.RAW_CANDIDATE: 2,
        CandidateStatus.BLOCKED_CANDIDATE: 3,
        CandidateStatus.NO_TRADE: 4,
    }
    return (
        status_rank.get(candidate.status, 99),
        -float(candidate.raw_score),
        candidate.strategy_id,
        candidate.movement_type,
        candidate.symbol,
    )


def _summarize(raw_items: list[RawPoolCandidate], candidates: tuple[StrategyCandidate, ...]) -> CandidatePoolSummary:
    return CandidatePoolSummary(
        input_count=len(raw_items),
        candidate_count=len(candidates),
        raw_count=sum(1 for candidate in candidates if candidate.status == CandidateStatus.RAW_CANDIDATE),
        valid_count=sum(1 for candidate in candidates if candidate.status in EXECUTABLE_LIKE_STATUSES),
        blocked_count=sum(1 for candidate in candidates if candidate.status == CandidateStatus.BLOCKED_CANDIDATE),
        no_trade_count=sum(1 for candidate in candidates if candidate.status == CandidateStatus.NO_TRADE),
    )


def _diagnostic(
    *,
    code: str,
    candidate_id: str,
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "candidate_id": candidate_id,
        "message": message,
        "is_order_action": False,
    }
    payload.update(extra)
    return payload


def _safe_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)] = value
        elif isinstance(value, (list, tuple)):
            safe[str(key)] = list(value)
        elif isinstance(value, dict):
            safe[str(key)] = dict(value)
        else:
            safe[str(key)] = str(value)
    return safe


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out

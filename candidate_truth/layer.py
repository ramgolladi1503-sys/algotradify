from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CandidateTruthStatus(StrEnum):
    REAL = "REAL"
    SYNTHETIC = "SYNTHETIC"
    FALLBACK = "FALLBACK"
    ADVISORY = "ADVISORY"
    MALFORMED = "MALFORMED"
    UNKNOWN = "UNKNOWN"


_SYNTHETIC_HINTS = ("synthetic", "mock", "demo", "simulated")
_FALLBACK_HINTS = ("fallback", "nearest", "substitute")
_ADVISORY_ACTIONS = {"ADVISORY", "ADVISORY_ONLY", "WATCH", "INFO"}
_MALFORMED_BLOCKERS = {
    "MISSING_CANDIDATE_ID",
    "MISSING_SYMBOL",
    "MISSING_STRATEGY_ID",
    "MISSING_SETUP_FAMILY",
}


@dataclass(frozen=True)
class CandidateTruthRecord:
    candidate_id: str
    symbol: str | None
    strategy_id: str | None
    setup_family: str | None
    truth_status: CandidateTruthStatus
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    normalized: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_candidate_truth_record(self) -> bool:
        return True

    @property
    def is_execution_decision(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "strategy_id": self.strategy_id,
            "setup_family": self.setup_family,
            "truth_status": self.truth_status.value,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "provenance": dict(self.provenance),
            "normalized": dict(self.normalized),
            "raw": dict(self.raw),
            "is_candidate_truth_record": self.is_candidate_truth_record,
            "is_execution_decision": self.is_execution_decision,
        }


def _as_dict(candidate: Any) -> dict[str, Any]:
    if hasattr(candidate, "to_dict") and callable(candidate.to_dict):
        raw = candidate.to_dict()
        return raw if isinstance(raw, dict) else {"raw_value": raw}
    if isinstance(candidate, dict):
        return dict(candidate)
    return {"raw_value": candidate}


def _first_present(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return value
    return None


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _contains_hint(raw: dict[str, Any], hints: tuple[str, ...]) -> bool:
    haystack = " ".join(str(value).lower() for value in raw.values() if value is not None)
    return any(hint in haystack for hint in hints)


def _classify(raw: dict[str, Any], blockers: list[str]) -> CandidateTruthStatus:
    if any(blocker in _MALFORMED_BLOCKERS for blocker in blockers):
        return CandidateTruthStatus.MALFORMED

    explicit = str(raw.get("truth_status") or raw.get("candidate_truth") or "").upper()
    if explicit in CandidateTruthStatus.__members__:
        return CandidateTruthStatus[explicit]
    if explicit in {item.value for item in CandidateTruthStatus}:
        return CandidateTruthStatus(explicit)

    final_action = str(raw.get("final_action") or raw.get("permission") or raw.get("bucket") or "").upper()
    if final_action in _ADVISORY_ACTIONS:
        return CandidateTruthStatus.ADVISORY

    if bool(raw.get("fallback_used")) or bool(raw.get("is_fallback")) or _contains_hint(raw, _FALLBACK_HINTS):
        return CandidateTruthStatus.FALLBACK

    if bool(raw.get("synthetic")) or bool(raw.get("is_synthetic")) or _contains_hint(raw, _SYNTHETIC_HINTS):
        return CandidateTruthStatus.SYNTHETIC

    if raw.get("is_execution_decision") is False or raw.get("entry_hypothesis") or raw.get("signal_features"):
        return CandidateTruthStatus.REAL

    return CandidateTruthStatus.UNKNOWN


def normalize_candidate(candidate: Any, *, source: str = "unknown") -> CandidateTruthRecord:
    raw = _as_dict(candidate)

    candidate_id = _first_present(raw, "candidate_id", "trade_id", "advisory_id", "id")
    symbol = _first_present(raw, "symbol", "underlying", "index_symbol")
    strategy_id = _first_present(raw, "strategy_id", "strategy", "strategy_family")
    setup_family = _first_present(raw, "setup_family", "strategy_family", "setup")

    blockers: list[str] = []
    if candidate_id is None:
        blockers.append("MISSING_CANDIDATE_ID")
    if symbol is None:
        blockers.append("MISSING_SYMBOL")
    if strategy_id is None:
        blockers.append("MISSING_STRATEGY_ID")
    if setup_family is None:
        blockers.append("MISSING_SETUP_FAMILY")

    blockers.extend(_listify(raw.get("blockers")))
    blockers.extend(_listify(raw.get("blocker")))
    blockers.extend(_listify(raw.get("first_blocker")))
    blockers.extend(_listify(raw.get("reason")) if raw.get("status") == "blocked" else [])

    warnings = _listify(raw.get("warnings"))
    warnings.extend(_listify(raw.get("warning")))

    normalized = {
        "candidate_id": str(candidate_id) if candidate_id is not None else "malformed:missing_candidate_id",
        "symbol": str(symbol).upper() if symbol is not None else None,
        "strategy_id": str(strategy_id) if strategy_id is not None else None,
        "setup_family": str(setup_family) if setup_family is not None else None,
        "direction": raw.get("direction"),
        "confidence": raw.get("confidence"),
        "score": raw.get("score") or raw.get("final_score") or raw.get("rank_score"),
        "entry_hypothesis": raw.get("entry_hypothesis"),
        "invalidation_hypothesis": raw.get("invalidation_hypothesis"),
        "required_data": raw.get("required_data") or [],
        "signal_features": raw.get("signal_features") or {},
    }

    provenance = dict(raw.get("provenance") or {})
    provenance.setdefault("source", source)
    provenance.setdefault("raw_keys", sorted(str(key) for key in raw.keys()))

    blockers = _dedupe(blockers)
    warnings = _dedupe(warnings)
    truth_status = _classify(raw, blockers)

    return CandidateTruthRecord(
        candidate_id=normalized["candidate_id"],
        symbol=normalized["symbol"],
        strategy_id=normalized["strategy_id"],
        setup_family=normalized["setup_family"],
        truth_status=truth_status,
        blockers=blockers,
        warnings=warnings,
        provenance=provenance,
        normalized=normalized,
        raw=raw,
    )


def normalize_candidates(candidates: list[Any], *, source: str = "unknown") -> list[CandidateTruthRecord]:
    return [normalize_candidate(candidate, source=source) for candidate in candidates]

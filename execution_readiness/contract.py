from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ExecutionReadinessStatus(StrEnum):
    ALLOWED = "ALLOWED"
    BLOCKED_CANDIDATE_TRUTH = "BLOCKED_CANDIDATE_TRUTH"
    BLOCKED_OPPORTUNITY = "BLOCKED_OPPORTUNITY"
    BLOCKED_BROKER_CONTRACT = "BLOCKED_BROKER_CONTRACT"
    BLOCKED_MARKET_READINESS = "BLOCKED_MARKET_READINESS"
    BLOCKED_RISK = "BLOCKED_RISK"
    BLOCKED_INCOMPLETE_EVIDENCE = "BLOCKED_INCOMPLETE_EVIDENCE"


@dataclass(frozen=True)
class RiskReadiness:
    allowed: bool
    status: str = "RISK_PLACEHOLDER"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "status": self.status,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class ExecutionReadiness:
    candidate_id: str
    execution_allowed: bool
    status: ExecutionReadinessStatus
    blockers: list[str]
    warnings: list[str]
    evidence: dict[str, Any]

    @property
    def is_execution_readiness_record(self) -> bool:
        return True

    @property
    def is_order(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "execution_allowed": self.execution_allowed,
            "status": self.status.value,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "is_execution_readiness_record": self.is_execution_readiness_record,
            "is_order": self.is_order,
        }


def build_execution_readiness(
    *,
    candidate_truth: dict[str, Any] | None,
    opportunity: dict[str, Any] | None,
    broker_contract: dict[str, Any] | None,
    market_readiness: dict[str, Any] | None,
    risk: RiskReadiness | dict[str, Any] | None = None,
) -> ExecutionReadiness:
    blockers: list[str] = []
    warnings: list[str] = []
    evidence = {
        "candidate_truth": candidate_truth,
        "opportunity": opportunity,
        "broker_contract": broker_contract,
        "market_readiness": market_readiness,
        "risk": _risk_to_dict(risk),
    }

    candidate_id = _candidate_id(candidate_truth, opportunity, broker_contract)

    if candidate_truth is None:
        blockers.append("MISSING_CANDIDATE_TRUTH")
    elif candidate_truth.get("truth_status") != "REAL":
        blockers.append(f"CANDIDATE_TRUTH_NOT_REAL:{candidate_truth.get('truth_status')}")
    else:
        blockers.extend(_prefixed(candidate_truth.get("blockers"), "CANDIDATE_TRUTH"))
        warnings.extend(_prefixed(candidate_truth.get("warnings"), "CANDIDATE_TRUTH"))

    if opportunity is None:
        blockers.append("MISSING_OPPORTUNITY")
    elif opportunity.get("opportunity_status") not in {"SELECTED", "RANKED"}:
        blockers.append(f"OPPORTUNITY_NOT_RANKABLE:{opportunity.get('opportunity_status')}")
    else:
        blockers.extend(_prefixed(opportunity.get("blockers"), "OPPORTUNITY"))
        warnings.extend(_prefixed(opportunity.get("warnings"), "OPPORTUNITY"))

    if broker_contract is None:
        blockers.append("MISSING_BROKER_CONTRACT_READINESS")
    elif broker_contract.get("readiness_status") not in {"RESOLVED_EXACT", "RESOLVED_FALLBACK"} or not broker_contract.get("resolved"):
        blockers.append(f"BROKER_CONTRACT_NOT_RESOLVED:{broker_contract.get('readiness_status')}")
    else:
        blockers.extend(_prefixed(broker_contract.get("blockers"), "BROKER_CONTRACT"))
        warnings.extend(_prefixed(broker_contract.get("warnings"), "BROKER_CONTRACT"))
        if broker_contract.get("fallback_used"):
            warnings.append("BROKER_CONTRACT:FALLBACK_USED")

    if market_readiness is None:
        blockers.append("MISSING_MARKET_READINESS")
    elif market_readiness.get("status") != "READY":
        blockers.append(f"MARKET_NOT_READY:{market_readiness.get('status')}")
    else:
        blockers.extend(_prefixed(market_readiness.get("blockers"), "MARKET"))
        warnings.extend(_prefixed(market_readiness.get("warnings"), "MARKET"))

    risk_payload = _risk_to_dict(risk)
    if risk_payload is None:
        blockers.append("MISSING_RISK_READINESS")
    elif not risk_payload.get("allowed"):
        blockers.append(f"RISK_NOT_ALLOWED:{risk_payload.get('status')}")
        blockers.extend(_prefixed(risk_payload.get("blockers"), "RISK"))
    else:
        blockers.extend(_prefixed(risk_payload.get("blockers"), "RISK"))
        warnings.extend(_prefixed(risk_payload.get("warnings"), "RISK"))

    blockers = _dedupe(blockers)
    warnings = _dedupe(warnings)
    execution_allowed = not blockers
    status = ExecutionReadinessStatus.ALLOWED if execution_allowed else _status_from_blockers(blockers)

    return ExecutionReadiness(
        candidate_id=candidate_id,
        execution_allowed=execution_allowed,
        status=status,
        blockers=blockers,
        warnings=warnings,
        evidence=evidence,
    )


def _status_from_blockers(blockers: list[str]) -> ExecutionReadinessStatus:
    if any(item.startswith("MISSING_") for item in blockers):
        return ExecutionReadinessStatus.BLOCKED_INCOMPLETE_EVIDENCE
    if any(item.startswith("CANDIDATE_TRUTH") for item in blockers):
        return ExecutionReadinessStatus.BLOCKED_CANDIDATE_TRUTH
    if any(item.startswith("OPPORTUNITY") for item in blockers):
        return ExecutionReadinessStatus.BLOCKED_OPPORTUNITY
    if any(item.startswith("BROKER_CONTRACT") for item in blockers):
        return ExecutionReadinessStatus.BLOCKED_BROKER_CONTRACT
    if any(item.startswith("MARKET") for item in blockers):
        return ExecutionReadinessStatus.BLOCKED_MARKET_READINESS
    if any(item.startswith("RISK") for item in blockers):
        return ExecutionReadinessStatus.BLOCKED_RISK
    return ExecutionReadinessStatus.BLOCKED_INCOMPLETE_EVIDENCE


def _risk_to_dict(risk: RiskReadiness | dict[str, Any] | None) -> dict[str, Any] | None:
    if risk is None:
        return None
    if isinstance(risk, RiskReadiness):
        return risk.to_dict()
    return dict(risk)


def _candidate_id(*payloads: dict[str, Any] | None) -> str:
    for payload in payloads:
        if isinstance(payload, dict) and payload.get("candidate_id"):
            return str(payload["candidate_id"])
    return "unknown"


def _prefixed(values: Any, prefix: str) -> list[str]:
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        values = [str(values)]
    return [f"{prefix}:{value}" for value in values if value not in (None, "")]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

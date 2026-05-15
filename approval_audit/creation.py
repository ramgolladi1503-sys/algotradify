from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from approval_audit.audit import ApprovalAuditEvent, ApprovalStatus, build_approval_event


@dataclass(frozen=True)
class ApprovalCreationRequest:
    candidate_id: str
    operator_id: str
    reason: str
    expires_at_epoch: float
    safety_decision: dict[str, Any]
    approval_id: str | None = None
    ts_epoch: float | None = None
    status: ApprovalStatus = ApprovalStatus.APPROVED
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "ApprovalCreationRequest":
        return ApprovalCreationRequest(
            candidate_id=self.candidate_id.strip(),
            operator_id=self.operator_id.strip(),
            reason=self.reason.strip(),
            expires_at_epoch=self.expires_at_epoch,
            safety_decision=dict(self.safety_decision),
            approval_id=self.approval_id.strip() if isinstance(self.approval_id, str) else self.approval_id,
            ts_epoch=self.ts_epoch,
            status=self.status,
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class ApprovalCreationResult:
    created: bool
    event: ApprovalAuditEvent | None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    append_path: str | None = None

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "event": self.event.to_dict() if self.event else None,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "append_path": self.append_path,
            "is_order_action": self.is_order_action,
        }


def validate_approval_creation(request: ApprovalCreationRequest) -> tuple[list[str], list[str]]:
    req = request.normalized()
    blockers: list[str] = []
    warnings: list[str] = []

    if not req.candidate_id or req.candidate_id.lower() == "unknown":
        blockers.append("CANDIDATE_ID_REQUIRED")
    if not req.operator_id or req.operator_id.lower() == "unknown":
        blockers.append("OPERATOR_ID_REQUIRED")
    if len(req.reason) < 8:
        blockers.append("APPROVAL_REASON_TOO_SHORT")
    if req.ts_epoch is not None and req.expires_at_epoch <= req.ts_epoch:
        blockers.append("APPROVAL_EXPIRY_MUST_BE_AFTER_TIMESTAMP")
    if req.expires_at_epoch <= 0:
        blockers.append("APPROVAL_EXPIRY_REQUIRED")
    if req.status not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
        blockers.append("APPROVAL_STATUS_MUST_BE_APPROVED_OR_REJECTED")

    safety = req.safety_decision
    if not isinstance(safety, dict) or not safety:
        blockers.append("SAFETY_DECISION_SNAPSHOT_REQUIRED")
    else:
        if "execution_permitted" not in safety:
            blockers.append("SAFETY_DECISION_EXECUTION_PERMITTED_REQUIRED")
        if "status" not in safety:
            blockers.append("SAFETY_DECISION_STATUS_REQUIRED")
        if safety.get("is_order_action") is not False:
            blockers.append("SAFETY_DECISION_ORDER_FLAG_UNSAFE")
        if safety.get("safety_visibility_only") is not True:
            warnings.append("SAFETY_DECISION_VISIBILITY_FLAG_MISSING")

    if req.approval_id and len(req.approval_id) < 4:
        blockers.append("APPROVAL_ID_TOO_SHORT")

    return _dedupe(blockers), _dedupe(warnings)


def create_approval_event(request: ApprovalCreationRequest) -> ApprovalCreationResult:
    req = request.normalized()
    blockers, warnings = validate_approval_creation(req)
    if blockers:
        return ApprovalCreationResult(created=False, event=None, blockers=blockers, warnings=warnings)

    approval_id = req.approval_id or _stable_approval_id(req)
    event = build_approval_event(
        approval_id=approval_id,
        candidate_id=req.candidate_id,
        operator_id=req.operator_id,
        reason=req.reason,
        status=req.status,
        ts_epoch=req.ts_epoch,
        expires_at_epoch=req.expires_at_epoch,
        safety_decision=req.safety_decision,
    )
    return ApprovalCreationResult(created=True, event=event, warnings=warnings)


def append_approval_event(path: Path, request: ApprovalCreationRequest) -> ApprovalCreationResult:
    result = create_approval_event(request)
    if not result.created or result.event is None:
        return result

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.event.to_dict(), sort_keys=True, separators=(",", ":")))
        handle.write("\n")
    return ApprovalCreationResult(
        created=True,
        event=result.event,
        warnings=list(result.warnings),
        append_path=str(path),
    )


def approval_request_from_mapping(payload: dict[str, Any]) -> ApprovalCreationRequest:
    status_raw = str(payload.get("status") or payload.get("approval_status") or "APPROVED").upper()
    status = ApprovalStatus.REJECTED if status_raw in {"REJECT", "REJECTED", "DENIED", "DENY"} else ApprovalStatus.APPROVED
    return ApprovalCreationRequest(
        approval_id=payload.get("approval_id"),
        candidate_id=str(payload.get("candidate_id") or ""),
        operator_id=str(payload.get("operator_id") or payload.get("approved_by") or ""),
        reason=str(payload.get("reason") or payload.get("approval_reason") or ""),
        expires_at_epoch=_float(payload.get("expires_at_epoch") or payload.get("expiry_epoch")),
        ts_epoch=_optional_float(payload.get("ts_epoch") or payload.get("approved_at_epoch")),
        safety_decision=payload.get("safety_decision") if isinstance(payload.get("safety_decision"), dict) else {},
        status=status,
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    )


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return _float(value)


def _stable_approval_id(req: ApprovalCreationRequest) -> str:
    seed = "|".join([
        req.candidate_id,
        req.operator_id,
        req.reason,
        str(req.ts_epoch or ""),
        str(req.expires_at_epoch),
        req.status.value,
    ])
    return f"approval-{sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out

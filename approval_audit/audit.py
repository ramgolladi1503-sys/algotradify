from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ApprovalStatus(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ApprovalAuditEvent:
    approval_id: str
    candidate_id: str
    operator_id: str
    status: ApprovalStatus
    reason: str
    ts_epoch: float | None = None
    expires_at_epoch: float | None = None
    safety_decision: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def immutable_audit_event(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    def is_expired(self, now_epoch: float | None = None) -> bool:
        if self.expires_at_epoch is None:
            return False
        if now_epoch is None:
            return False
        return now_epoch >= self.expires_at_epoch

    def to_dict(self, *, now_epoch: float | None = None) -> dict[str, Any]:
        status = ApprovalStatus.EXPIRED if self.status == ApprovalStatus.APPROVED and self.is_expired(now_epoch) else self.status
        return {
            "approval_id": self.approval_id,
            "candidate_id": self.candidate_id,
            "operator_id": self.operator_id,
            "status": status.value,
            "reason": self.reason,
            "ts_epoch": self.ts_epoch,
            "expires_at_epoch": self.expires_at_epoch,
            "safety_decision": dict(self.safety_decision),
            "raw": dict(self.raw),
            "immutable_audit_event": self.immutable_audit_event,
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class ApprovalAuditSummary:
    candidate_id: str
    current_status: ApprovalStatus
    approval_id: str | None
    operator_id: str | None
    events: list[ApprovalAuditEvent]
    approved_count: int
    rejected_count: int
    expired_count: int
    revoked_count: int
    latest_reason: str | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self, *, now_epoch: float | None = None) -> dict[str, Any]:
        events = [event.to_dict(now_epoch=now_epoch) for event in self.events]
        current_status = self.current_status
        if events:
            current_status = ApprovalStatus(events[-1]["status"])
        return {
            "candidate_id": self.candidate_id,
            "current_status": current_status.value,
            "approval_id": self.approval_id,
            "operator_id": self.operator_id,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "expired_count": self.expired_count,
            "revoked_count": self.revoked_count,
            "latest_reason": self.latest_reason,
            "events": events,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "is_order_action": self.is_order_action,
        }


def build_approval_event(
    *,
    approval_id: str,
    candidate_id: str,
    operator_id: str,
    reason: str,
    status: ApprovalStatus = ApprovalStatus.APPROVED,
    ts_epoch: float | None = None,
    expires_at_epoch: float | None = None,
    safety_decision: dict[str, Any] | None = None,
) -> ApprovalAuditEvent:
    return ApprovalAuditEvent(
        approval_id=approval_id,
        candidate_id=candidate_id,
        operator_id=operator_id,
        status=status,
        reason=reason,
        ts_epoch=ts_epoch,
        expires_at_epoch=expires_at_epoch,
        safety_decision=safety_decision or {},
        raw={
            "approval_id": approval_id,
            "candidate_id": candidate_id,
            "operator_id": operator_id,
            "status": status.value,
            "reason": reason,
            "ts_epoch": ts_epoch,
            "expires_at_epoch": expires_at_epoch,
            "safety_decision": safety_decision or {},
        },
    )


def normalize_approval_audit(records: list[dict[str, Any]], *, candidate_id: str | None = None, now_epoch: float | None = None) -> ApprovalAuditSummary:
    events = [_event_from_record(row) for row in records if isinstance(row, dict)]
    if candidate_id:
        events = [event for event in events if event.candidate_id == candidate_id]
    events.sort(key=lambda event: (event.ts_epoch is None, event.ts_epoch or 0.0))

    resolved_candidate_id = candidate_id or _first_candidate_id(events) or "unknown"
    if not events:
        return ApprovalAuditSummary(
            candidate_id=resolved_candidate_id,
            current_status=ApprovalStatus.UNKNOWN,
            approval_id=None,
            operator_id=None,
            events=[],
            approved_count=0,
            rejected_count=0,
            expired_count=0,
            revoked_count=0,
            blockers=["NO_APPROVAL_AUDIT_EVENTS"],
        )

    latest = events[-1]
    latest_status = ApprovalStatus.EXPIRED if latest.status == ApprovalStatus.APPROVED and latest.is_expired(now_epoch) else latest.status
    return ApprovalAuditSummary(
        candidate_id=resolved_candidate_id,
        current_status=latest_status,
        approval_id=latest.approval_id,
        operator_id=latest.operator_id,
        events=events,
        approved_count=sum(1 for event in events if event.status == ApprovalStatus.APPROVED and not event.is_expired(now_epoch)),
        rejected_count=sum(1 for event in events if event.status == ApprovalStatus.REJECTED),
        expired_count=sum(1 for event in events if event.status == ApprovalStatus.EXPIRED or event.is_expired(now_epoch)),
        revoked_count=sum(1 for event in events if event.status == ApprovalStatus.REVOKED),
        latest_reason=latest.reason,
        blockers=[] if latest_status == ApprovalStatus.APPROVED else [f"APPROVAL_{latest_status.value}"],
        warnings=_warnings(events),
    )


def _event_from_record(row: dict[str, Any]) -> ApprovalAuditEvent:
    safety_decision = row.get("safety_decision") if isinstance(row.get("safety_decision"), dict) else {}
    return ApprovalAuditEvent(
        approval_id=str(row.get("approval_id") or row.get("id") or "unknown"),
        candidate_id=str(row.get("candidate_id") or row.get("trade_id") or "unknown"),
        operator_id=str(row.get("operator_id") or row.get("approved_by") or row.get("user_id") or "unknown"),
        status=_normalize_status(row.get("status") or row.get("approval_status")),
        reason=str(row.get("reason") or row.get("approval_reason") or "unspecified"),
        ts_epoch=_num(row.get("ts_epoch") or row.get("timestamp") or row.get("approved_at_epoch")),
        expires_at_epoch=_num(row.get("expires_at_epoch") or row.get("expires_at") or row.get("expiry_epoch")),
        safety_decision=safety_decision,
        raw=dict(row),
    )


def _normalize_status(value: Any) -> ApprovalStatus:
    key = str(value or "").upper().strip().replace(" ", "_").replace("-", "_")
    if key in {"APPROVE", "APPROVED", "ALLOW", "ALLOWED"}:
        return ApprovalStatus.APPROVED
    if key in {"REJECT", "REJECTED", "DENY", "DENIED"}:
        return ApprovalStatus.REJECTED
    if key in {"EXPIRE", "EXPIRED"}:
        return ApprovalStatus.EXPIRED
    if key in {"REVOKE", "REVOKED", "CANCELLED", "CANCELED"}:
        return ApprovalStatus.REVOKED
    return ApprovalStatus.UNKNOWN


def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_candidate_id(events: list[ApprovalAuditEvent]) -> str | None:
    for event in events:
        if event.candidate_id != "unknown":
            return event.candidate_id
    return None


def _warnings(events: list[ApprovalAuditEvent]) -> list[str]:
    warnings: list[str] = []
    if any(event.operator_id == "unknown" for event in events):
        warnings.append("UNKNOWN_OPERATOR_PRESENT")
    if any(event.approval_id == "unknown" for event in events):
        warnings.append("UNKNOWN_APPROVAL_ID_PRESENT")
    if any(event.status == ApprovalStatus.UNKNOWN for event in events):
        warnings.append("UNKNOWN_APPROVAL_STATUS_PRESENT")
    return warnings

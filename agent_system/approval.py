from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agent_system.scope_guard import AgentScopeDecision
from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION


@dataclass(frozen=True)
class AgentApprovalDecision:
    schema_version: int
    work_id: str | None
    approved: bool
    state: str
    approved_by: str | None
    allowed_for_patch: bool
    allowed_for_runtime_wiring: bool
    allowed_for_broker_api: bool
    allowed_for_live_execution: bool
    is_order_action: bool
    broker_api_called: bool
    live_mode_touched: bool
    blockers: tuple[str, ...]
    reasons: tuple[str, ...]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        payload["reasons"] = list(self.reasons)
        payload["metadata"] = dict(self.metadata)
        return payload


def agent_approval_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": "agent_approval_v1",
        "states": ["APPROVED_FOR_PATCH", "REJECTED"],
        "safe_defaults": {
            "allowed_for_runtime_wiring": False,
            "allowed_for_broker_api": False,
            "allowed_for_live_execution": False,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
        },
        "scope": "patch_approval_only_no_runtime_no_broker_no_live_no_execution",
    }


def _clean_approved_by(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def approve_agent_work(
    scope_decision: AgentScopeDecision,
    *,
    human_approved: bool = False,
    approved_by: str | None = None,
) -> AgentApprovalDecision:
    """Convert a scope decision into a patch-only approval decision.

    Approval never grants runtime wiring, broker API, live execution, or order-action rights.
    """

    blockers: list[str] = []
    reasons: list[str] = []
    approved_by_clean = _clean_approved_by(approved_by)

    if not scope_decision.accepted:
        blockers.append("SCOPE_DECISION_NOT_ACCEPTED")

    if scope_decision.state == "BLOCKED":
        blockers.append("BLOCKED_WORK_CANNOT_BE_APPROVED")

    if scope_decision.requires_human_approval:
        if not human_approved:
            blockers.append("HUMAN_APPROVAL_REQUIRED")
        if human_approved and not approved_by_clean:
            blockers.append("APPROVED_BY_REQUIRED")

    if scope_decision.is_order_action:
        blockers.append("ORDER_ACTION_FORBIDDEN")

    if scope_decision.broker_api_called or scope_decision.allowed_for_broker_api:
        blockers.append("BROKER_API_FORBIDDEN")

    if scope_decision.live_mode_touched or scope_decision.allowed_for_live_execution:
        blockers.append("LIVE_EXECUTION_FORBIDDEN")

    if scope_decision.allowed_for_runtime_wiring:
        blockers.append("RUNTIME_WIRING_FORBIDDEN")

    approved = not blockers
    state = "APPROVED_FOR_PATCH" if approved else "REJECTED"

    if approved:
        reasons.append("agent_work_approved_for_patch_only")
        if scope_decision.requires_human_approval:
            reasons.append("human_approval_recorded")
        else:
            reasons.append("scope_guard_patch_approval_accepted")
    else:
        reasons.append("agent_work_approval_rejected")

    return AgentApprovalDecision(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        work_id=scope_decision.work_id,
        approved=approved,
        state=state,
        approved_by=approved_by_clean if approved and human_approved else None,
        allowed_for_patch=approved,
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        allowed_for_live_execution=False,
        is_order_action=False,
        broker_api_called=False,
        live_mode_touched=False,
        blockers=tuple(sorted(set(blockers))),
        reasons=tuple(sorted(set(reasons))),
        metadata={
            "contract": "agent_approval_v1",
            "scope": "patch_approval_only_no_runtime_no_broker_no_live_no_execution",
        },
    )

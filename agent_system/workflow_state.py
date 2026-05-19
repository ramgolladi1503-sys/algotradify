from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from agent_system.role_registry import AgentRole, SAFE_ROLE_FLAGS
from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION


AGENT_WORKFLOW_STATE_CONTRACT = "agent_workflow_state_machine_v1"


class AgentWorkflowState(str, Enum):
    REQUESTED = "REQUESTED"
    SCOPED_BY_SCOPE_OWNER = "SCOPED_BY_SCOPE_OWNER"
    REVIEWED_BY_GRILL = "REVIEWED_BY_GRILL"
    DESIGNED_BY_HERMES = "DESIGNED_BY_HERMES"
    IMPLEMENTED_BY_GSD = "IMPLEMENTED_BY_GSD"
    REVIEWED_BY_QA_SAFETY = "REVIEWED_BY_QA_SAFETY"
    EVIDENCE_RECORDED = "EVIDENCE_RECORDED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    MERGE_READY = "MERGE_READY"

    BLOCKED_SCOPE = "BLOCKED_SCOPE"
    BLOCKED_SAFETY = "BLOCKED_SAFETY"
    BLOCKED_MISSING_EVIDENCE = "BLOCKED_MISSING_EVIDENCE"
    BLOCKED_FORBIDDEN_PATH = "BLOCKED_FORBIDDEN_PATH"
    BLOCKED_UNAPPROVED_PATCH = "BLOCKED_UNAPPROVED_PATCH"


TERMINAL_BLOCKED_STATES = frozenset(
    {
        AgentWorkflowState.BLOCKED_SCOPE.value,
        AgentWorkflowState.BLOCKED_SAFETY.value,
        AgentWorkflowState.BLOCKED_MISSING_EVIDENCE.value,
        AgentWorkflowState.BLOCKED_FORBIDDEN_PATH.value,
        AgentWorkflowState.BLOCKED_UNAPPROVED_PATCH.value,
    }
)

ORDERED_ACTIVE_STATES = (
    AgentWorkflowState.REQUESTED.value,
    AgentWorkflowState.SCOPED_BY_SCOPE_OWNER.value,
    AgentWorkflowState.REVIEWED_BY_GRILL.value,
    AgentWorkflowState.DESIGNED_BY_HERMES.value,
    AgentWorkflowState.IMPLEMENTED_BY_GSD.value,
    AgentWorkflowState.REVIEWED_BY_QA_SAFETY.value,
    AgentWorkflowState.EVIDENCE_RECORDED.value,
    AgentWorkflowState.HUMAN_APPROVED.value,
    AgentWorkflowState.MERGE_READY.value,
)

ROLE_REQUIRED_TRANSITIONS: dict[str, tuple[str, str]] = {
    AgentRole.SCOPE_OWNER.value: (
        AgentWorkflowState.REQUESTED.value,
        AgentWorkflowState.SCOPED_BY_SCOPE_OWNER.value,
    ),
    AgentRole.GRILL_REVIEWER.value: (
        AgentWorkflowState.SCOPED_BY_SCOPE_OWNER.value,
        AgentWorkflowState.REVIEWED_BY_GRILL.value,
    ),
    AgentRole.HERMES_ARCHITECT.value: (
        AgentWorkflowState.REVIEWED_BY_GRILL.value,
        AgentWorkflowState.DESIGNED_BY_HERMES.value,
    ),
    AgentRole.GSD_IMPLEMENTER.value: (
        AgentWorkflowState.DESIGNED_BY_HERMES.value,
        AgentWorkflowState.IMPLEMENTED_BY_GSD.value,
    ),
    AgentRole.QA_SAFETY_REVIEWER.value: (
        AgentWorkflowState.IMPLEMENTED_BY_GSD.value,
        AgentWorkflowState.REVIEWED_BY_QA_SAFETY.value,
    ),
    AgentRole.EVIDENCE_RECORDER.value: (
        AgentWorkflowState.REVIEWED_BY_QA_SAFETY.value,
        AgentWorkflowState.EVIDENCE_RECORDED.value,
    ),
    AgentRole.HUMAN_APPROVER.value: (
        AgentWorkflowState.EVIDENCE_RECORDED.value,
        AgentWorkflowState.HUMAN_APPROVED.value,
    ),
}

MERGE_READY_TRANSITION = (
    AgentRole.HUMAN_APPROVER.value,
    AgentWorkflowState.HUMAN_APPROVED.value,
    AgentWorkflowState.MERGE_READY.value,
)

BLOCKED_STATE_REASONS = {
    AgentWorkflowState.BLOCKED_SCOPE.value: "scope_blocked",
    AgentWorkflowState.BLOCKED_SAFETY.value: "safety_blocked",
    AgentWorkflowState.BLOCKED_MISSING_EVIDENCE.value: "missing_evidence_blocked",
    AgentWorkflowState.BLOCKED_FORBIDDEN_PATH.value: "forbidden_path_blocked",
    AgentWorkflowState.BLOCKED_UNAPPROVED_PATCH.value: "unapproved_patch_blocked",
}


@dataclass(frozen=True)
class AgentWorkflowDecision:
    schema_version: int
    contract: str
    accepted: bool
    current_state: str
    target_state: str
    role_id: str
    new_state: str
    blockers: tuple[str, ...]
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    read_only: bool
    is_order_action: bool
    broker_api_called: bool
    live_mode_touched: bool
    allowed_for_live_execution: bool
    real_order_id: None
    allowed_for_runtime_wiring: bool
    allowed_for_broker_api: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        payload["reasons"] = list(self.reasons)
        payload["warnings"] = list(self.warnings)
        payload["metadata"] = dict(self.metadata)
        return payload


def _normalize_state(value: str) -> str:
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    allowed = {state.value for state in AgentWorkflowState}
    if normalized not in allowed:
        raise ValueError(f"UNKNOWN_AGENT_WORKFLOW_STATE:{value}")
    return normalized


def _normalize_role(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    allowed = {role.value for role in AgentRole}
    if normalized not in allowed:
        raise ValueError(f"UNKNOWN_AGENT_ROLE:{value}")
    return normalized


def _decision(
    *,
    accepted: bool,
    current_state: str,
    target_state: str,
    role_id: str,
    new_state: str,
    blockers: tuple[str, ...] = (),
    reasons: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> AgentWorkflowDecision:
    return AgentWorkflowDecision(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        contract=AGENT_WORKFLOW_STATE_CONTRACT,
        accepted=accepted,
        current_state=current_state,
        target_state=target_state,
        role_id=role_id,
        new_state=new_state,
        blockers=tuple(sorted(set(blockers))),
        reasons=tuple(sorted(set(reasons))),
        warnings=tuple(sorted(set(warnings))),
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        metadata={
            "scope": "workflow_state_machine_only_no_validator_no_ci_no_execution",
            "ordered_active_states": list(ORDERED_ACTIVE_STATES),
        },
        **SAFE_ROLE_FLAGS,
    )


def evaluate_agent_workflow_transition(
    *,
    current_state: str,
    target_state: str,
    role_id: str,
    required_outputs_present: bool = True,
    safety_review_passed: bool = True,
    evidence_recorded: bool = True,
    human_approved: bool = False,
) -> AgentWorkflowDecision:
    """Evaluate a role-based workflow transition.

    This is PR 12 only. It validates lifecycle order and role ownership. It does not
    parse handoff artifacts, inspect changed files, run CI, or execute work.
    """

    current = _normalize_state(current_state)
    target = _normalize_state(target_state)
    role = _normalize_role(role_id)

    if current in TERMINAL_BLOCKED_STATES:
        return _decision(
            accepted=False,
            current_state=current,
            target_state=target,
            role_id=role,
            new_state=current,
            blockers=("CURRENT_STATE_TERMINAL_BLOCKED",),
            reasons=("blocked_state_cannot_transition",),
        )

    if target in TERMINAL_BLOCKED_STATES:
        return _decision(
            accepted=True,
            current_state=current,
            target_state=target,
            role_id=role,
            new_state=target,
            reasons=(BLOCKED_STATE_REASONS[target],),
        )

    if target == AgentWorkflowState.MERGE_READY.value:
        required_role, required_current, required_target = MERGE_READY_TRANSITION
        blockers: list[str] = []
        if role != required_role:
            blockers.append("MERGE_READY_REQUIRES_HUMAN_APPROVER")
        if current != required_current:
            blockers.append("MERGE_READY_REQUIRES_HUMAN_APPROVED_STATE")
        if target != required_target:
            blockers.append("INVALID_MERGE_READY_TARGET")
        if not required_outputs_present:
            blockers.append("REQUIRED_OUTPUTS_MISSING")
        if not safety_review_passed:
            blockers.append("SAFETY_REVIEW_NOT_PASSED")
        if not evidence_recorded:
            blockers.append("EVIDENCE_NOT_RECORDED")
        if not human_approved:
            blockers.append("HUMAN_APPROVAL_REQUIRED")
        if blockers:
            return _decision(
                accepted=False,
                current_state=current,
                target_state=target,
                role_id=role,
                new_state=current,
                blockers=tuple(blockers),
                reasons=("merge_ready_transition_rejected",),
            )
        return _decision(
            accepted=True,
            current_state=current,
            target_state=target,
            role_id=role,
            new_state=target,
            reasons=("merge_ready_transition_accepted",),
        )

    expected = ROLE_REQUIRED_TRANSITIONS.get(role)
    if expected is None:
        return _decision(
            accepted=False,
            current_state=current,
            target_state=target,
            role_id=role,
            new_state=current,
            blockers=("ROLE_HAS_NO_WORKFLOW_TRANSITION",),
            reasons=("role_transition_rejected",),
        )

    expected_current, expected_target = expected
    blockers = []
    if current != expected_current:
        blockers.append("CURRENT_STATE_INVALID_FOR_ROLE")
    if target != expected_target:
        blockers.append("TARGET_STATE_INVALID_FOR_ROLE")
    if not required_outputs_present:
        blockers.append("REQUIRED_OUTPUTS_MISSING")
    if target == AgentWorkflowState.REVIEWED_BY_QA_SAFETY.value and not safety_review_passed:
        blockers.append("SAFETY_REVIEW_NOT_PASSED")
    if target == AgentWorkflowState.EVIDENCE_RECORDED.value and not evidence_recorded:
        blockers.append("EVIDENCE_NOT_RECORDED")
    if target == AgentWorkflowState.HUMAN_APPROVED.value and not human_approved:
        blockers.append("HUMAN_APPROVAL_REQUIRED")

    if blockers:
        return _decision(
            accepted=False,
            current_state=current,
            target_state=target,
            role_id=role,
            new_state=current,
            blockers=tuple(blockers),
            reasons=("role_transition_rejected",),
        )

    return _decision(
        accepted=True,
        current_state=current,
        target_state=target,
        role_id=role,
        new_state=target,
        reasons=("role_transition_accepted",),
    )


def replay_agent_workflow(transitions: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> dict[str, Any]:
    """Replay an ordered transition list and return the final workflow status.

    This is deterministic and in-memory only. It does not read files or mutate task storage.
    """

    state = AgentWorkflowState.REQUESTED.value
    decisions: list[dict[str, Any]] = []
    for transition in transitions:
        decision = evaluate_agent_workflow_transition(
            current_state=state,
            target_state=str(transition.get("target_state", "")),
            role_id=str(transition.get("role_id", "")),
            required_outputs_present=bool(transition.get("required_outputs_present", True)),
            safety_review_passed=bool(transition.get("safety_review_passed", True)),
            evidence_recorded=bool(transition.get("evidence_recorded", True)),
            human_approved=bool(transition.get("human_approved", False)),
        )
        decisions.append(decision.to_dict())
        state = decision.new_state
        if not decision.accepted or state in TERMINAL_BLOCKED_STATES:
            break

    return {
        "contract": AGENT_WORKFLOW_STATE_CONTRACT,
        "initial_state": AgentWorkflowState.REQUESTED.value,
        "final_state": state,
        "merge_ready": state == AgentWorkflowState.MERGE_READY.value,
        "decision_count": len(decisions),
        "decisions": decisions,
        "allowed_for_runtime_wiring": False,
        "allowed_for_broker_api": False,
        **SAFE_ROLE_FLAGS,
    }


def agent_workflow_state_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": AGENT_WORKFLOW_STATE_CONTRACT,
        "ordered_active_states": list(ORDERED_ACTIVE_STATES),
        "blocked_states": sorted(TERMINAL_BLOCKED_STATES),
        "role_required_transitions": {
            role: {"from": current, "to": target}
            for role, (current, target) in ROLE_REQUIRED_TRANSITIONS.items()
        },
        "merge_ready_transition": {
            "role_id": MERGE_READY_TRANSITION[0],
            "from": MERGE_READY_TRANSITION[1],
            "to": MERGE_READY_TRANSITION[2],
        },
        "safe_flags": dict(SAFE_ROLE_FLAGS),
        "scope": "workflow_state_machine_only_no_handoff_validator_no_ci_no_execution",
    }


def validate_agent_workflow_state_machine() -> dict[str, Any]:
    blockers: list[str] = []
    if ORDERED_ACTIVE_STATES[0] != AgentWorkflowState.REQUESTED.value:
        blockers.append("WORKFLOW_MUST_START_REQUESTED")
    if ORDERED_ACTIVE_STATES[-1] != AgentWorkflowState.MERGE_READY.value:
        blockers.append("WORKFLOW_MUST_END_MERGE_READY")
    if set(ROLE_REQUIRED_TRANSITIONS) != {
        AgentRole.SCOPE_OWNER.value,
        AgentRole.GRILL_REVIEWER.value,
        AgentRole.HERMES_ARCHITECT.value,
        AgentRole.GSD_IMPLEMENTER.value,
        AgentRole.QA_SAFETY_REVIEWER.value,
        AgentRole.EVIDENCE_RECORDER.value,
        AgentRole.HUMAN_APPROVER.value,
    }:
        blockers.append("WORKFLOW_ROLE_TRANSITIONS_INCOMPLETE")

    return {
        "contract": AGENT_WORKFLOW_STATE_CONTRACT,
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "ordered_state_count": len(ORDERED_ACTIVE_STATES),
        "blocked_state_count": len(TERMINAL_BLOCKED_STATES),
        "allowed_for_runtime_wiring": False,
        "allowed_for_broker_api": False,
        **SAFE_ROLE_FLAGS,
    }

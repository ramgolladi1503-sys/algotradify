import pytest

from agent_system.workflow_state import (
    AGENT_WORKFLOW_STATE_CONTRACT,
    ORDERED_ACTIVE_STATES,
    ROLE_REQUIRED_TRANSITIONS,
    TERMINAL_BLOCKED_STATES,
    agent_workflow_state_schema_contract,
    evaluate_agent_workflow_transition,
    replay_agent_workflow,
    validate_agent_workflow_state_machine,
)


def test_schema_contract_exposes_ordered_role_flow_and_safe_flags():
    contract = agent_workflow_state_schema_contract()

    assert contract["contract"] == AGENT_WORKFLOW_STATE_CONTRACT
    assert contract["ordered_active_states"] == [
        "REQUESTED",
        "SCOPED_BY_SCOPE_OWNER",
        "REVIEWED_BY_GRILL",
        "DESIGNED_BY_HERMES",
        "IMPLEMENTED_BY_GSD",
        "REVIEWED_BY_QA_SAFETY",
        "EVIDENCE_RECORDED",
        "HUMAN_APPROVED",
        "MERGE_READY",
    ]
    assert contract["safe_flags"] == {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
        "real_order_id": None,
    }
    assert contract["scope"] == "workflow_state_machine_only_no_handoff_validator_no_ci_no_execution"
    assert set(contract["role_required_transitions"]) == {
        "scope_owner",
        "grill_reviewer",
        "hermes_architect",
        "gsd_implementer",
        "qa_safety_reviewer",
        "evidence_recorder",
        "human_approver",
    }


def test_validate_workflow_state_machine_passes_default_contract():
    result = validate_agent_workflow_state_machine()

    assert result["valid"] is True
    assert result["blockers"] == []
    assert result["ordered_state_count"] == 9
    assert result["blocked_state_count"] == 5
    assert result["is_order_action"] is False
    assert result["broker_api_called"] is False
    assert result["live_mode_touched"] is False
    assert result["allowed_for_live_execution"] is False
    assert result["real_order_id"] is None


def test_happy_path_transitions_to_merge_ready():
    transitions = [
        {"role_id": "scope_owner", "target_state": "SCOPED_BY_SCOPE_OWNER"},
        {"role_id": "grill_reviewer", "target_state": "REVIEWED_BY_GRILL"},
        {"role_id": "hermes_architect", "target_state": "DESIGNED_BY_HERMES"},
        {"role_id": "gsd_implementer", "target_state": "IMPLEMENTED_BY_GSD"},
        {"role_id": "qa_safety_reviewer", "target_state": "REVIEWED_BY_QA_SAFETY"},
        {"role_id": "evidence_recorder", "target_state": "EVIDENCE_RECORDED"},
        {"role_id": "human_approver", "target_state": "HUMAN_APPROVED", "human_approved": True},
        {"role_id": "human_approver", "target_state": "MERGE_READY", "human_approved": True},
    ]

    result = replay_agent_workflow(transitions)

    assert result["merge_ready"] is True
    assert result["final_state"] == "MERGE_READY"
    assert result["decision_count"] == 8
    assert all(decision["accepted"] for decision in result["decisions"])


def test_requested_cannot_jump_directly_to_gsd_implementation():
    decision = evaluate_agent_workflow_transition(
        current_state="REQUESTED",
        target_state="IMPLEMENTED_BY_GSD",
        role_id="gsd_implementer",
    )

    assert decision.accepted is False
    assert decision.new_state == "REQUESTED"
    assert "CURRENT_STATE_INVALID_FOR_ROLE" in decision.blockers


def test_hermes_design_cannot_jump_to_merge_ready():
    decision = evaluate_agent_workflow_transition(
        current_state="DESIGNED_BY_HERMES",
        target_state="MERGE_READY",
        role_id="human_approver",
        human_approved=True,
    )

    assert decision.accepted is False
    assert decision.new_state == "DESIGNED_BY_HERMES"
    assert "MERGE_READY_REQUIRES_HUMAN_APPROVED_STATE" in decision.blockers


def test_implementation_cannot_go_to_human_approved_without_qa_safety_and_evidence():
    decision = evaluate_agent_workflow_transition(
        current_state="IMPLEMENTED_BY_GSD",
        target_state="HUMAN_APPROVED",
        role_id="human_approver",
        human_approved=True,
    )

    assert decision.accepted is False
    assert decision.new_state == "IMPLEMENTED_BY_GSD"
    assert "CURRENT_STATE_INVALID_FOR_ROLE" in decision.blockers


def test_gsd_cannot_implement_before_hermes_design():
    decision = evaluate_agent_workflow_transition(
        current_state="REVIEWED_BY_GRILL",
        target_state="IMPLEMENTED_BY_GSD",
        role_id="gsd_implementer",
    )

    assert decision.accepted is False
    assert "CURRENT_STATE_INVALID_FOR_ROLE" in decision.blockers


def test_scope_owner_cannot_skip_grill_review():
    decision = evaluate_agent_workflow_transition(
        current_state="REQUESTED",
        target_state="DESIGNED_BY_HERMES",
        role_id="scope_owner",
    )

    assert decision.accepted is False
    assert "TARGET_STATE_INVALID_FOR_ROLE" in decision.blockers


def test_qa_safety_transition_requires_safety_review_passed():
    decision = evaluate_agent_workflow_transition(
        current_state="IMPLEMENTED_BY_GSD",
        target_state="REVIEWED_BY_QA_SAFETY",
        role_id="qa_safety_reviewer",
        safety_review_passed=False,
    )

    assert decision.accepted is False
    assert "SAFETY_REVIEW_NOT_PASSED" in decision.blockers


def test_evidence_transition_requires_evidence_recorded():
    decision = evaluate_agent_workflow_transition(
        current_state="REVIEWED_BY_QA_SAFETY",
        target_state="EVIDENCE_RECORDED",
        role_id="evidence_recorder",
        evidence_recorded=False,
    )

    assert decision.accepted is False
    assert "EVIDENCE_NOT_RECORDED" in decision.blockers


def test_human_approval_transition_requires_human_approval_flag():
    decision = evaluate_agent_workflow_transition(
        current_state="EVIDENCE_RECORDED",
        target_state="HUMAN_APPROVED",
        role_id="human_approver",
        human_approved=False,
    )

    assert decision.accepted is False
    assert "HUMAN_APPROVAL_REQUIRED" in decision.blockers


def test_merge_ready_requires_all_final_gates():
    decision = evaluate_agent_workflow_transition(
        current_state="HUMAN_APPROVED",
        target_state="MERGE_READY",
        role_id="human_approver",
        required_outputs_present=False,
        safety_review_passed=False,
        evidence_recorded=False,
        human_approved=False,
    )

    assert decision.accepted is False
    assert decision.new_state == "HUMAN_APPROVED"
    assert set(decision.blockers) == {
        "REQUIRED_OUTPUTS_MISSING",
        "SAFETY_REVIEW_NOT_PASSED",
        "EVIDENCE_NOT_RECORDED",
        "HUMAN_APPROVAL_REQUIRED",
    }


def test_merge_ready_requires_human_approver_role():
    decision = evaluate_agent_workflow_transition(
        current_state="HUMAN_APPROVED",
        target_state="MERGE_READY",
        role_id="gsd_implementer",
        human_approved=True,
    )

    assert decision.accepted is False
    assert "MERGE_READY_REQUIRES_HUMAN_APPROVER" in decision.blockers


def test_blocked_state_is_terminal():
    decision = evaluate_agent_workflow_transition(
        current_state="BLOCKED_SCOPE",
        target_state="SCOPED_BY_SCOPE_OWNER",
        role_id="scope_owner",
    )

    assert decision.accepted is False
    assert decision.new_state == "BLOCKED_SCOPE"
    assert decision.blockers == ("CURRENT_STATE_TERMINAL_BLOCKED",)


def test_role_can_move_to_blocked_state_when_failure_is_detected():
    decision = evaluate_agent_workflow_transition(
        current_state="SCOPED_BY_SCOPE_OWNER",
        target_state="BLOCKED_SCOPE",
        role_id="grill_reviewer",
    )

    assert decision.accepted is True
    assert decision.new_state == "BLOCKED_SCOPE"
    assert decision.reasons == ("scope_blocked",)


def test_replay_stops_after_first_rejected_transition():
    result = replay_agent_workflow(
        [
            {"role_id": "scope_owner", "target_state": "SCOPED_BY_SCOPE_OWNER"},
            {"role_id": "gsd_implementer", "target_state": "IMPLEMENTED_BY_GSD"},
            {"role_id": "human_approver", "target_state": "MERGE_READY", "human_approved": True},
        ]
    )

    assert result["merge_ready"] is False
    assert result["final_state"] == "SCOPED_BY_SCOPE_OWNER"
    assert result["decision_count"] == 2
    assert result["decisions"][-1]["accepted"] is False


def test_replay_stops_after_blocked_state():
    result = replay_agent_workflow(
        [
            {"role_id": "scope_owner", "target_state": "SCOPED_BY_SCOPE_OWNER"},
            {"role_id": "grill_reviewer", "target_state": "BLOCKED_SCOPE"},
            {"role_id": "hermes_architect", "target_state": "DESIGNED_BY_HERMES"},
        ]
    )

    assert result["merge_ready"] is False
    assert result["final_state"] == "BLOCKED_SCOPE"
    assert result["decision_count"] == 2


def test_unknown_state_fails_closed():
    with pytest.raises(ValueError, match="UNKNOWN_AGENT_WORKFLOW_STATE"):
        evaluate_agent_workflow_transition(
            current_state="WISHFUL_THINKING",
            target_state="MERGE_READY",
            role_id="human_approver",
        )


def test_unknown_role_fails_closed():
    with pytest.raises(ValueError, match="UNKNOWN_AGENT_ROLE"):
        evaluate_agent_workflow_transition(
            current_state="REQUESTED",
            target_state="SCOPED_BY_SCOPE_OWNER",
            role_id="scrum_master",
        )


def test_decision_to_dict_uses_lists_and_preserves_safe_flags():
    decision = evaluate_agent_workflow_transition(
        current_state="REQUESTED",
        target_state="SCOPED_BY_SCOPE_OWNER",
        role_id="scope_owner",
    )
    payload = decision.to_dict()

    assert payload["accepted"] is True
    assert isinstance(payload["blockers"], list)
    assert isinstance(payload["reasons"], list)
    assert isinstance(payload["warnings"], list)
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["live_mode_touched"] is False
    assert payload["allowed_for_live_execution"] is False
    assert payload["real_order_id"] is None
    assert payload["allowed_for_runtime_wiring"] is False
    assert payload["allowed_for_broker_api"] is False


def test_transition_constants_cover_expected_roles_and_states():
    assert ORDERED_ACTIVE_STATES[0] == "REQUESTED"
    assert ORDERED_ACTIVE_STATES[-1] == "MERGE_READY"
    assert "BLOCKED_SAFETY" in TERMINAL_BLOCKED_STATES
    assert ROLE_REQUIRED_TRANSITIONS["gsd_implementer"] == (
        "DESIGNED_BY_HERMES",
        "IMPLEMENTED_BY_GSD",
    )

import pytest

from agent_system.role_registry import (
    AGENT_ROLE_REGISTRY_CONTRACT,
    FORBIDDEN_ROLE_ACTIONS,
    SAFE_ROLE_FLAGS,
    AgentRole,
    agent_role_registry_schema_contract,
    assess_role_request,
    build_agent_role_registry,
    get_agent_role_contract,
    validate_agent_role_registry,
)
from agent_system.work_contract import AgentAction


def test_role_registry_contains_exact_locked_roles():
    registry = build_agent_role_registry()

    assert set(registry) == {role.value for role in AgentRole}
    assert list(registry) == [
        "scope_owner",
        "grill_reviewer",
        "hermes_architect",
        "gsd_implementer",
        "qa_safety_reviewer",
        "evidence_recorder",
        "human_approver",
    ]


def test_role_registry_schema_contract_is_non_executing():
    contract = agent_role_registry_schema_contract()

    assert contract["contract"] == AGENT_ROLE_REGISTRY_CONTRACT
    assert contract["safe_flags"] == SAFE_ROLE_FLAGS
    assert contract["scope"] == "role_registry_only_no_workflow_no_validator_no_ci_no_execution"
    assert "PLACE_ORDER" in contract["forbidden_actions"]
    assert "broker_contract/" in contract["forbidden_path_prefixes"]
    assert "agent_system/" in contract["high_risk_path_prefixes"]


def test_validate_agent_role_registry_passes_default_registry():
    result = validate_agent_role_registry()

    assert result["valid"] is True
    assert result["blockers"] == []
    assert result["role_count"] == 7
    assert result["is_order_action"] is False
    assert result["broker_api_called"] is False
    assert result["live_mode_touched"] is False
    assert result["allowed_for_live_execution"] is False
    assert result["real_order_id"] is None


def test_no_role_allows_forbidden_trading_actions():
    registry = build_agent_role_registry()

    for role in registry.values():
        assert set(role.allowed_actions).isdisjoint(FORBIDDEN_ROLE_ACTIONS)
        assert AgentAction.PLACE_ORDER.value not in role.allowed_actions
        assert AgentAction.CALL_BROKER_API.value not in role.allowed_actions
        assert AgentAction.ENABLE_LIVE.value not in role.allowed_actions
        assert role.allowed_for_runtime_wiring is False
        assert role.allowed_for_broker_api is False
        assert role.allowed_for_live_execution is False
        assert role.is_order_action is False
        assert role.broker_api_called is False
        assert role.live_mode_touched is False
        assert role.real_order_id is None


def test_hermes_architect_can_define_contract_but_cannot_generate_patch():
    allowed = assess_role_request(
        role_id="hermes_architect",
        source_agent="hermes",
        action="DEFINE_CONTRACT",
        requested_paths=["docs/agent-role-registry.md"],
    )
    blocked = assess_role_request(
        role_id="hermes_architect",
        source_agent="hermes",
        action="GENERATE_PATCH",
        requested_paths=["agent_system/role_registry.py"],
        human_approved=True,
    )

    assert allowed["accepted"] is True
    assert allowed["state"] == "ROLE_REQUEST_ALLOWED"
    assert blocked["accepted"] is False
    assert "ACTION_NOT_ALLOWED_FOR_ROLE" in blocked["blockers"]


def test_grill_reviewer_can_review_but_cannot_generate_code():
    allowed = assess_role_request(
        role_id="grill_reviewer",
        source_agent="grill_me",
        action="REVIEW_PR",
        requested_paths=["docs/pr-handoffs/AGENT-PR11-grill.md"],
    )
    blocked = assess_role_request(
        role_id="grill_reviewer",
        source_agent="grill_me",
        action="GENERATE_PATCH",
        requested_paths=["agent_system/role_registry.py"],
    )

    assert allowed["accepted"] is True
    assert blocked["accepted"] is False
    assert "ACTION_NOT_ALLOWED_FOR_ROLE" in blocked["blockers"]


def test_gsd_implementer_can_generate_patch_in_agent_system_with_human_approval():
    result = assess_role_request(
        role_id="gsd_implementer",
        source_agent="gsd",
        action="GENERATE_PATCH",
        requested_paths=["agent_system/role_registry.py", "tests/test_agent_role_registry.py"],
        human_approved=True,
    )

    assert result["accepted"] is True
    assert result["blockers"] == []
    assert result["warnings"] == []
    assert result["allowed_for_runtime_wiring"] is False
    assert result["allowed_for_broker_api"] is False
    assert result["allowed_for_live_execution"] is False


def test_gsd_implementer_high_risk_path_requires_human_approval():
    result = assess_role_request(
        role_id="gsd_implementer",
        source_agent="gsd",
        action="GENERATE_PATCH",
        requested_paths=["agent_system/role_registry.py"],
    )

    assert result["accepted"] is False
    assert result["blockers"] == []
    assert result["warnings"] == ["HIGH_RISK_PATH_REQUIRES_HUMAN_APPROVAL"]


def test_gsd_implementer_cannot_touch_broker_live_path_even_with_human_approval():
    result = assess_role_request(
        role_id="gsd_implementer",
        source_agent="gsd",
        action="GENERATE_PATCH",
        requested_paths=["broker_contract/client.py"],
        human_approved=True,
    )

    assert result["accepted"] is False
    assert "FORBIDDEN_PATH_FOR_ROLE" in result["blockers"]
    assert "PATH_OUTSIDE_ROLE_ALLOWED_PREFIXES" in result["blockers"]


def test_qa_safety_reviewer_cannot_modify_implementation():
    role = get_agent_role_contract("qa-safety-reviewer")
    result = assess_role_request(
        role_id="qa_safety_reviewer",
        source_agent="grill_me",
        action="GENERATE_PATCH",
        requested_paths=["agent_system/role_registry.py"],
        human_approved=True,
    )

    assert role.may_review_safety is True
    assert role.may_modify_implementation is False
    assert result["accepted"] is False
    assert "ACTION_NOT_ALLOWED_FOR_ROLE" in result["blockers"]


def test_evidence_recorder_cannot_approve_merge():
    role = get_agent_role_contract("evidence_recorder")
    result = assess_role_request(
        role_id="evidence_recorder",
        source_agent="manual",
        action="AUDIT_RISK",
        requested_paths=["docs/pr-handoffs/AGENT-PR11-evidence.md"],
    )

    assert role.may_record_evidence is True
    assert role.may_approve_merge is False
    assert result["accepted"] is False
    assert "ACTION_NOT_ALLOWED_FOR_ROLE" in result["blockers"]


def test_human_approver_can_review_but_cannot_bypass_forbidden_action():
    allowed = assess_role_request(
        role_id="human approver",
        source_agent="manual",
        action="REVIEW_PR",
        requested_paths=["docs/pr-handoffs/AGENT-PR11-evidence.md"],
    )
    blocked = assess_role_request(
        role_id="human_approver",
        source_agent="manual",
        action="PLACE_ORDER",
        requested_paths=["docs/pr-handoffs/AGENT-PR11-evidence.md"],
    )

    assert allowed["accepted"] is True
    assert blocked["accepted"] is False
    assert "ACTION_NOT_ALLOWED_FOR_ROLE" in blocked["blockers"]
    assert "FORBIDDEN_ACTION_FOR_ROLE" in blocked["blockers"]


def test_role_request_blocks_wrong_source_for_role():
    result = assess_role_request(
        role_id="hermes_architect",
        source_agent="gsd",
        action="DEFINE_CONTRACT",
        requested_paths=["docs/agent-role-registry.md"],
    )

    assert result["accepted"] is False
    assert "SOURCE_AGENT_NOT_ALLOWED_FOR_ROLE" in result["blockers"]


def test_role_request_requires_paths():
    result = assess_role_request(
        role_id="grill_reviewer",
        source_agent="grill_me",
        action="REVIEW_PR",
        requested_paths=[],
    )

    assert result["accepted"] is False
    assert "REQUESTED_PATHS_MISSING" in result["blockers"]


def test_unknown_role_fails_closed():
    with pytest.raises(KeyError, match="UNKNOWN_AGENT_ROLE"):
        get_agent_role_contract("scrum_master")

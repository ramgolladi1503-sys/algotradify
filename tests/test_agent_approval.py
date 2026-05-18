from dataclasses import replace

from agent_system.approval import agent_approval_schema_contract, approve_agent_work
from agent_system.scope_guard import assess_agent_scope
from agent_system.work_contract import normalize_agent_work_request


def _request(**overrides):
    payload = {
        "schema_version": 1,
        "source_agent": "gsd",
        "action": "GENERATE_TESTS",
        "title": "Add approval tests",
        "scope": "Add behavior tests for patch-only approval decisions.",
        "allowed_paths": ["tests/"],
        "requested_paths": ["tests/test_agent_approval.py"],
        "forbidden_paths": ["credentials.py", ".env", "broker_contract/"],
        "requires_human_approval": False,
        "metadata": {"project": "algotradify"},
    }
    payload.update(overrides)
    return normalize_agent_work_request(payload)


def _scope(**overrides):
    return assess_agent_scope(_request(**overrides))


def test_schema_contract_is_patch_only_and_non_executing():
    contract = agent_approval_schema_contract()

    assert contract["contract"] == "agent_approval_v1"
    assert contract["states"] == ["APPROVED_FOR_PATCH", "REJECTED"]
    assert contract["safe_defaults"] == {
        "allowed_for_runtime_wiring": False,
        "allowed_for_broker_api": False,
        "allowed_for_live_execution": False,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
    }
    assert contract["scope"] == "patch_approval_only_no_runtime_no_broker_no_live_no_execution"


def test_low_risk_scope_is_approved_for_patch_only():
    scope_decision = _scope()
    approval = approve_agent_work(scope_decision)

    assert approval.approved is True
    assert approval.state == "APPROVED_FOR_PATCH"
    assert approval.allowed_for_patch is True
    assert approval.approved_by is None
    assert approval.blockers == ()
    assert approval.allowed_for_runtime_wiring is False
    assert approval.allowed_for_broker_api is False
    assert approval.allowed_for_live_execution is False
    assert approval.is_order_action is False
    assert approval.broker_api_called is False
    assert approval.live_mode_touched is False
    assert "agent_work_approved_for_patch_only" in approval.reasons


def test_blocked_scope_cannot_be_approved():
    scope_decision = _scope(action="PLACE_ORDER")
    approval = approve_agent_work(scope_decision, human_approved=True, approved_by="ram")

    assert approval.approved is False
    assert approval.state == "REJECTED"
    assert approval.allowed_for_patch is False
    assert approval.approved_by is None
    assert "SCOPE_DECISION_NOT_ACCEPTED" in approval.blockers
    assert "BLOCKED_WORK_CANNOT_BE_APPROVED" in approval.blockers


def test_human_approval_required_blocks_without_human_approval():
    scope_decision = _scope(
        action="GENERATE_PATCH",
        allowed_paths=["agent_system/"],
        requested_paths=["agent_system/approval.py"],
    )
    approval = approve_agent_work(scope_decision)

    assert scope_decision.state == "WAITING_HUMAN_APPROVAL"
    assert approval.approved is False
    assert approval.state == "REJECTED"
    assert "HUMAN_APPROVAL_REQUIRED" in approval.blockers


def test_human_approval_requires_approved_by():
    scope_decision = _scope(
        action="GENERATE_PATCH",
        allowed_paths=["agent_system/"],
        requested_paths=["agent_system/approval.py"],
    )
    approval = approve_agent_work(scope_decision, human_approved=True, approved_by=" ")

    assert approval.approved is False
    assert "APPROVED_BY_REQUIRED" in approval.blockers


def test_human_approved_medium_risk_scope_is_patch_only():
    scope_decision = _scope(
        action="GENERATE_PATCH",
        allowed_paths=["agent_system/"],
        requested_paths=["agent_system/approval.py"],
    )
    approval = approve_agent_work(scope_decision, human_approved=True, approved_by="ram")

    assert approval.approved is True
    assert approval.state == "APPROVED_FOR_PATCH"
    assert approval.approved_by == "ram"
    assert approval.allowed_for_patch is True
    assert approval.allowed_for_runtime_wiring is False
    assert approval.allowed_for_broker_api is False
    assert approval.allowed_for_live_execution is False
    assert "human_approval_recorded" in approval.reasons


def test_order_action_scope_flag_blocks_approval_even_if_scope_claims_accepted():
    scope_decision = replace(_scope(), is_order_action=True)
    approval = approve_agent_work(scope_decision)

    assert approval.approved is False
    assert "ORDER_ACTION_FORBIDDEN" in approval.blockers
    assert approval.is_order_action is False


def test_broker_api_scope_flag_blocks_approval():
    scope_decision = replace(_scope(), allowed_for_broker_api=True)
    approval = approve_agent_work(scope_decision)

    assert approval.approved is False
    assert "BROKER_API_FORBIDDEN" in approval.blockers
    assert approval.allowed_for_broker_api is False


def test_live_scope_flag_blocks_approval():
    scope_decision = replace(_scope(), allowed_for_live_execution=True)
    approval = approve_agent_work(scope_decision)

    assert approval.approved is False
    assert "LIVE_EXECUTION_FORBIDDEN" in approval.blockers
    assert approval.allowed_for_live_execution is False


def test_runtime_wiring_scope_flag_blocks_approval():
    scope_decision = replace(_scope(), allowed_for_runtime_wiring=True)
    approval = approve_agent_work(scope_decision)

    assert approval.approved is False
    assert "RUNTIME_WIRING_FORBIDDEN" in approval.blockers
    assert approval.allowed_for_runtime_wiring is False


def test_to_dict_converts_tuple_fields_to_lists():
    approval = approve_agent_work(_scope())
    payload = approval.to_dict()

    assert isinstance(payload["blockers"], list)
    assert isinstance(payload["reasons"], list)
    assert payload["metadata"] == {
        "contract": "agent_approval_v1",
        "scope": "patch_approval_only_no_runtime_no_broker_no_live_no_execution",
    }

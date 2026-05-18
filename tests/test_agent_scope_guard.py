from agent_system.scope_guard import (
    FORBIDDEN_PATH_PREFIXES,
    HIGH_RISK_PATH_PREFIXES,
    LOW_RISK_PATH_PREFIXES,
    SOURCE_ALLOWED_ACTIONS,
    agent_scope_guard_schema_contract,
    assess_agent_scope,
)
from agent_system.work_contract import AgentAction, build_agent_work_id, normalize_agent_work_request


def _request(**overrides):
    payload = {
        "schema_version": 1,
        "source_agent": "gsd",
        "action": "GENERATE_TESTS",
        "title": "Add scope guard tests",
        "scope": "Add behavior tests for the safe agent scope guard.",
        "allowed_paths": ["tests/"],
        "requested_paths": ["tests/test_agent_scope_guard.py"],
        "forbidden_paths": ["credentials.py", ".env", "broker_contract/"],
        "requires_human_approval": False,
        "metadata": {"project": "algotradify"},
    }
    payload.update(overrides)
    return normalize_agent_work_request(payload)


def test_schema_contract_exposes_safe_defaults_and_path_sets():
    contract = agent_scope_guard_schema_contract()

    assert contract["contract"] == "agent_scope_guard_v1"
    assert contract["safe_defaults"] == {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_runtime_wiring": False,
        "allowed_for_broker_api": False,
        "allowed_for_live_execution": False,
    }
    assert "gsd" in contract["source_allowed_actions"]
    assert "PLACE_ORDER" in contract["forbidden_actions"]
    assert list(FORBIDDEN_PATH_PREFIXES) == contract["forbidden_path_prefixes"]
    assert list(HIGH_RISK_PATH_PREFIXES) == contract["high_risk_path_prefixes"]
    assert list(LOW_RISK_PATH_PREFIXES) == contract["low_risk_path_prefixes"]
    assert contract["scope"] == "scope_guard_only_no_api_no_ui_no_broker_no_live_no_paper_orders"


def test_gsd_can_generate_tests_inside_allowed_path():
    request = _request()
    decision = assess_agent_scope(request)

    assert decision.accepted is True
    assert decision.state == "APPROVED_FOR_PATCH"
    assert decision.risk_level == "LOW"
    assert decision.allowed_for_patch is True
    assert decision.requires_human_approval is False
    assert decision.work_id == build_agent_work_id(request)
    assert decision.blockers == ()
    assert decision.reasons == ("low_risk_docs_or_tests_scope_approved",)


def test_decision_is_always_non_executing_even_when_patch_allowed():
    decision = assess_agent_scope(_request())

    assert decision.read_only is True
    assert decision.is_order_action is False
    assert decision.broker_api_called is False
    assert decision.live_mode_touched is False
    assert decision.allowed_for_runtime_wiring is False
    assert decision.allowed_for_broker_api is False
    assert decision.allowed_for_live_execution is False


def test_grill_me_cannot_generate_patch():
    decision = assess_agent_scope(_request(source_agent="grill_me", action="GENERATE_PATCH"))

    assert decision.accepted is False
    assert decision.state == "BLOCKED"
    assert decision.risk_level == "BLOCKED"
    assert decision.allowed_for_patch is False
    assert decision.work_id is None
    assert "ACTION_NOT_ALLOWED_FOR_SOURCE_AGENT" in decision.blockers


def test_grill_me_can_review_docs_scope():
    decision = assess_agent_scope(
        _request(
            source_agent="grill_me",
            action="REVIEW_PR",
            allowed_paths=["docs/"],
            requested_paths=["docs/agent-scope-guard.md"],
        )
    )

    assert decision.accepted is True
    assert decision.state == "APPROVED_FOR_PATCH"
    assert decision.allowed_for_patch is True


def test_hermes_can_define_contract_in_docs_scope():
    decision = assess_agent_scope(
        _request(
            source_agent="hermes",
            action="DEFINE_CONTRACT",
            allowed_paths=["docs/"],
            requested_paths=["docs/agent-scope-guard.md"],
        )
    )

    assert decision.accepted is True
    assert decision.allowed_for_patch is True


def test_hermes_cannot_touch_broker_runtime_path():
    decision = assess_agent_scope(
        _request(
            source_agent="hermes",
            action="DEFINE_CONTRACT",
            allowed_paths=["broker_contract/"],
            requested_paths=["broker_contract/order_gateway.py"],
        )
    )

    assert decision.accepted is False
    assert "FORBIDDEN_PATH_REQUESTED" in decision.blockers


def test_order_action_is_blocked():
    decision = assess_agent_scope(_request(action="PLACE_ORDER"))

    assert decision.accepted is False
    assert decision.state == "BLOCKED"
    assert "ACTION_FORBIDDEN" in decision.blockers
    assert "ORDER_ACTION_FORBIDDEN" in decision.blockers
    assert decision.is_order_action is False
    assert decision.allowed_for_patch is False


def test_broker_api_action_is_blocked():
    decision = assess_agent_scope(_request(action="CALL_BROKER_API"))

    assert decision.accepted is False
    assert "ACTION_FORBIDDEN" in decision.blockers
    assert "BROKER_API_FORBIDDEN" in decision.blockers
    assert decision.broker_api_called is False
    assert decision.allowed_for_broker_api is False


def test_live_action_is_blocked():
    decision = assess_agent_scope(_request(action="ENABLE_LIVE"))

    assert decision.accepted is False
    assert "ACTION_FORBIDDEN" in decision.blockers
    assert "LIVE_ACTION_FORBIDDEN" in decision.blockers
    assert decision.live_mode_touched is False
    assert decision.allowed_for_live_execution is False


def test_risk_gate_disable_is_blocked():
    decision = assess_agent_scope(_request(action="DISABLE_RISK_GATE"))

    assert decision.accepted is False
    assert "ACTION_FORBIDDEN" in decision.blockers


def test_forbidden_path_is_blocked():
    decision = assess_agent_scope(
        _request(
            allowed_paths=["credentials.py"],
            requested_paths=["credentials.py"],
        )
    )

    assert decision.accepted is False
    assert "FORBIDDEN_PATH_REQUESTED" in decision.blockers


def test_env_path_is_blocked_even_if_allowed():
    decision = assess_agent_scope(_request(allowed_paths=[".env"], requested_paths=[".env"]))

    assert decision.accepted is False
    assert "FORBIDDEN_PATH_REQUESTED" in decision.blockers


def test_broker_contract_path_is_blocked_even_if_allowed():
    decision = assess_agent_scope(
        _request(allowed_paths=["broker_contract/"], requested_paths=["broker_contract/client.py"])
    )

    assert decision.accepted is False
    assert "FORBIDDEN_PATH_REQUESTED" in decision.blockers


def test_requested_path_explicitly_forbidden_blocks():
    decision = assess_agent_scope(
        _request(
            allowed_paths=["tests/"],
            requested_paths=["tests/unsafe.py"],
            forbidden_paths=["tests/unsafe.py"],
        )
    )

    assert decision.accepted is False
    assert "REQUESTED_PATH_EXPLICITLY_FORBIDDEN" in decision.blockers


def test_requested_path_outside_allowed_paths_blocks():
    decision = assess_agent_scope(
        _request(
            allowed_paths=["docs/"],
            requested_paths=["tests/test_agent_scope_guard.py"],
        )
    )

    assert decision.accepted is False
    assert "REQUESTED_PATH_OUTSIDE_ALLOWED_PATHS" in decision.blockers


def test_high_risk_path_requires_human_approval():
    request = _request(
        action="GENERATE_PATCH",
        allowed_paths=["paper_trading/"],
        requested_paths=["paper_trading/proposals.py"],
    )
    decision = assess_agent_scope(request)

    assert decision.accepted is True
    assert decision.state == "WAITING_HUMAN_APPROVAL"
    assert decision.risk_level == "HIGH"
    assert decision.allowed_for_patch is False
    assert decision.requires_human_approval is True
    assert decision.work_id == build_agent_work_id(request)
    assert decision.warnings == ("HIGH_RISK_PATH_REQUIRES_HUMAN_APPROVAL",)
    assert decision.reasons == ("high_risk_scope_requires_human_approval",)


def test_medium_risk_non_docs_tests_path_requires_human_approval():
    request = _request(
        action="GENERATE_PATCH",
        allowed_paths=["agent_system/"],
        requested_paths=["agent_system/scope_guard.py"],
    )
    decision = assess_agent_scope(request)

    assert decision.accepted is True
    assert decision.state == "WAITING_HUMAN_APPROVAL"
    assert decision.risk_level == "MEDIUM"
    assert decision.allowed_for_patch is False
    assert decision.requires_human_approval is True
    assert decision.reasons == ("medium_risk_scope_requires_human_approval",)


def test_missing_requested_paths_blocks_when_constructed_object_is_empty():
    request = _request()
    empty_request = type(request)(
        schema_version=request.schema_version,
        source_agent=request.source_agent,
        action=request.action,
        title=request.title,
        scope=request.scope,
        allowed_paths=request.allowed_paths,
        requested_paths=(),
        forbidden_paths=request.forbidden_paths,
        requires_human_approval=request.requires_human_approval,
        metadata=request.metadata,
    )
    decision = assess_agent_scope(empty_request)

    assert decision.accepted is False
    assert "REQUESTED_PATHS_MISSING" in decision.blockers


def test_source_allowed_actions_matrix_is_restrictive():
    assert AgentAction.GENERATE_PATCH.value not in SOURCE_ALLOWED_ACTIONS["grill_me"]
    assert AgentAction.CALL_BROKER_API.value not in SOURCE_ALLOWED_ACTIONS["gsd"]
    assert AgentAction.ENABLE_LIVE.value not in SOURCE_ALLOWED_ACTIONS["hermes"]
    assert AgentAction.PLACE_ORDER.value in SOURCE_ALLOWED_ACTIONS["manual"]


def test_manual_source_still_cannot_perform_forbidden_action():
    decision = assess_agent_scope(_request(source_agent="manual", action="PLACE_ORDER"))

    assert decision.accepted is False
    assert "ACTION_FORBIDDEN" in decision.blockers
    assert "ORDER_ACTION_FORBIDDEN" in decision.blockers


def test_scope_decision_to_dict_uses_lists_for_reasons_and_blockers():
    decision = assess_agent_scope(_request(action="PLACE_ORDER"))
    payload = decision.to_dict()

    assert isinstance(payload["blockers"], list)
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["reasons"], list)
    assert payload["metadata"] == {
        "contract": "agent_scope_guard_v1",
        "scope": "agent_work_intake_guard_only_no_execution",
    }

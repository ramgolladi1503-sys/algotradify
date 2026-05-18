import pytest

from agent_system.work_contract import (
    AGENT_WORK_SCHEMA_VERSION,
    FORBIDDEN_AGENT_ACTIONS,
    SAFE_AGENT_ACTIONS,
    AgentAction,
    AgentWorkValidationError,
    agent_work_schema_contract,
    build_agent_work_id,
    normalize_agent_work_request,
)


def _payload(**overrides):
    payload = {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "source_agent": "gsd",
        "action": "GENERATE_TESTS",
        "title": "Add agent work contract tests",
        "scope": "Add deterministic contract tests for agent work request normalization.",
        "allowed_paths": ["tests/"],
        "requested_paths": ["tests/test_agent_work_contract.py"],
        "forbidden_paths": ["credentials.py", ".env", "broker_contract/"],
        "requires_human_approval": False,
        "metadata": {"project": "algotradify"},
    }
    payload.update(overrides)
    return payload


def test_normalize_valid_agent_work_request():
    request = normalize_agent_work_request(_payload())

    assert request.schema_version == AGENT_WORK_SCHEMA_VERSION
    assert request.source_agent == "gsd"
    assert request.action == "GENERATE_TESTS"
    assert request.title == "Add agent work contract tests"
    assert request.scope.startswith("Add deterministic")
    assert request.allowed_paths == ("tests/",)
    assert request.requested_paths == ("tests/test_agent_work_contract.py",)
    assert request.forbidden_paths == ("credentials.py", ".env", "broker_contract/")
    assert request.requires_human_approval is False
    assert request.metadata == {"project": "algotradify"}


def test_to_dict_converts_tuple_fields_to_lists():
    request = normalize_agent_work_request(_payload())

    data = request.to_dict()

    assert data["allowed_paths"] == ["tests/"]
    assert data["requested_paths"] == ["tests/test_agent_work_contract.py"]
    assert data["forbidden_paths"] == ["credentials.py", ".env", "broker_contract/"]


def test_source_agent_is_normalized_from_alias():
    request = normalize_agent_work_request(_payload(source_agent="Grill Me", action="REVIEW_PR"))

    assert request.source_agent == "grill_me"
    assert request.action == "REVIEW_PR"


def test_action_is_normalized_from_spaces_and_lowercase():
    request = normalize_agent_work_request(_payload(action="generate patch"))

    assert request.action == "GENERATE_PATCH"


def test_requested_paths_are_required():
    with pytest.raises(AgentWorkValidationError, match="REQUESTED_PATHS_MISSING"):
        normalize_agent_work_request(_payload(requested_paths=[]))


def test_path_fields_must_be_lists_not_strings():
    with pytest.raises(AgentWorkValidationError, match="REQUESTED_PATHS_MUST_BE_LIST"):
        normalize_agent_work_request(_payload(requested_paths="tests/test_agent_work_contract.py"))


def test_path_items_must_be_strings():
    with pytest.raises(AgentWorkValidationError, match="REQUESTED_PATHS_ITEM_MUST_BE_STRING"):
        normalize_agent_work_request(_payload(requested_paths=["tests/ok.py", 123]))


def test_payload_must_be_object():
    with pytest.raises(AgentWorkValidationError, match="AGENT_WORK_PAYLOAD_MUST_BE_OBJECT"):
        normalize_agent_work_request(["not", "a", "mapping"])


def test_missing_source_agent_blocks_normalization():
    with pytest.raises(AgentWorkValidationError, match="SOURCE_AGENT_MISSING"):
        normalize_agent_work_request(_payload(source_agent=""))


def test_unknown_source_agent_blocks_normalization():
    with pytest.raises(AgentWorkValidationError, match="SOURCE_AGENT_UNKNOWN"):
        normalize_agent_work_request(_payload(source_agent="random_bot"))


def test_missing_action_blocks_normalization():
    with pytest.raises(AgentWorkValidationError, match="ACTION_MISSING"):
        normalize_agent_work_request(_payload(action=""))


def test_unknown_action_blocks_normalization():
    with pytest.raises(AgentWorkValidationError, match="ACTION_UNKNOWN"):
        normalize_agent_work_request(_payload(action="MAKE_MAGIC"))


def test_empty_title_blocks_normalization():
    with pytest.raises(AgentWorkValidationError, match="TITLE_MISSING"):
        normalize_agent_work_request(_payload(title=" "))


def test_empty_scope_blocks_normalization():
    with pytest.raises(AgentWorkValidationError, match="SCOPE_MISSING"):
        normalize_agent_work_request(_payload(scope=" "))


def test_metadata_must_be_object():
    with pytest.raises(AgentWorkValidationError, match="METADATA_MUST_BE_OBJECT"):
        normalize_agent_work_request(_payload(metadata=["bad"]))


def test_schema_version_must_match_contract():
    with pytest.raises(AgentWorkValidationError, match="SCHEMA_VERSION_UNSUPPORTED"):
        normalize_agent_work_request(_payload(schema_version=999))


def test_forbidden_actions_are_representable_but_not_safe():
    request = normalize_agent_work_request(_payload(action="PLACE_ORDER"))

    assert request.action == AgentAction.PLACE_ORDER.value
    assert request.action in FORBIDDEN_AGENT_ACTIONS
    assert request.action not in SAFE_AGENT_ACTIONS


def test_safe_action_set_does_not_include_forbidden_trading_actions():
    assert AgentAction.PLACE_ORDER.value not in SAFE_AGENT_ACTIONS
    assert AgentAction.CALL_BROKER_API.value not in SAFE_AGENT_ACTIONS
    assert AgentAction.CHANGE_LIVE_CONFIG.value not in SAFE_AGENT_ACTIONS
    assert FORBIDDEN_AGENT_ACTIONS.isdisjoint(SAFE_AGENT_ACTIONS)


def test_build_agent_work_id_is_deterministic_for_same_identity():
    request_a = normalize_agent_work_request(_payload(metadata={"x": 1}))
    request_b = normalize_agent_work_request(_payload(metadata={"x": 2}))

    assert build_agent_work_id(request_a) == build_agent_work_id(request_b)


def test_build_agent_work_id_changes_when_identity_changes():
    request_a = normalize_agent_work_request(_payload())
    request_b = normalize_agent_work_request(_payload(title="Different title"))

    assert build_agent_work_id(request_a) != build_agent_work_id(request_b)


def test_schema_contract_exposes_safe_defaults_and_no_runtime_scope():
    contract = agent_work_schema_contract()

    assert contract["schema_version"] == AGENT_WORK_SCHEMA_VERSION
    assert contract["contract"] == "agent_work_request_v1"
    assert contract["safe_defaults"] == {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
        "real_order_id": None,
    }
    assert contract["scope"] == "contract_only_no_api_no_ui_no_broker_no_live_no_paper_orders"
    assert AgentAction.PLACE_ORDER.value in contract["forbidden_actions"]
    assert AgentAction.GENERATE_TESTS.value in contract["safe_actions"]

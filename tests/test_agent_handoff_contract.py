import pytest

from agent_system.handoff_contract import (
    AGENT_HANDOFF_CONTRACT,
    REQUIRED_HANDOFF_FIELDS,
    REQUIRED_SAFE_FLAGS,
    AgentHandoffValidationError,
    agent_handoff_schema_contract,
    build_minimal_handoff_payload,
    normalize_agent_handoff_artifact,
    validate_agent_handoff_payload,
)
from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION


def _payload(**overrides):
    payload = build_minimal_handoff_payload(
        task_id="AGENT-PR13",
        role_id="hermes_architect",
        workflow_state="REVIEWED_BY_GRILL",
        target_state="DESIGNED_BY_HERMES",
    )
    payload.update(overrides)
    return payload


def test_schema_contract_exposes_required_fields_and_safe_flags():
    contract = agent_handoff_schema_contract()

    assert contract["contract"] == AGENT_HANDOFF_CONTRACT
    assert contract["required_fields"] == list(REQUIRED_HANDOFF_FIELDS)
    assert contract["required_safe_flags"] == REQUIRED_SAFE_FLAGS
    assert contract["scope"] == "handoff_artifact_contract_only_no_validator_no_ci_no_execution"
    assert "hermes_architect" in contract["roles"]
    assert "DESIGNED_BY_HERMES" in contract["workflow_states"]
    assert "APPROVED" in contract["verdicts"]


def test_normalize_valid_handoff_artifact():
    artifact = normalize_agent_handoff_artifact(_payload())

    assert artifact.schema_version == AGENT_WORK_SCHEMA_VERSION
    assert artifact.contract == AGENT_HANDOFF_CONTRACT
    assert artifact.task_id == "AGENT-PR13"
    assert artifact.role_id == "hermes_architect"
    assert artifact.workflow_state == "REVIEWED_BY_GRILL"
    assert artifact.target_state == "DESIGNED_BY_HERMES"
    assert artifact.verdict == "APPROVED"
    assert artifact.safe_flags == REQUIRED_SAFE_FLAGS
    assert artifact.metadata["scope"] == "handoff_artifact_contract_only_no_repo_scan_no_ci_no_execution"


def test_to_dict_serializes_tuple_fields_as_lists():
    payload = normalize_agent_handoff_artifact(_payload()).to_dict()

    assert isinstance(payload["files_allowed"], list)
    assert isinstance(payload["files_forbidden"], list)
    assert isinstance(payload["risks_found"], list)
    assert isinstance(payload["tests_required"], list)
    assert isinstance(payload["acceptance_gates"], list)
    assert isinstance(payload["required_outputs"], list)
    assert isinstance(payload["blockers"], list)
    assert isinstance(payload["warnings"], list)


def test_missing_required_field_fails_closed():
    payload = _payload()
    payload.pop("acceptance_gates")

    with pytest.raises(AgentHandoffValidationError, match="HANDOFF_REQUIRED_FIELDS_MISSING"):
        normalize_agent_handoff_artifact(payload)


def test_wrong_contract_fails_closed():
    with pytest.raises(AgentHandoffValidationError, match="CONTRACT_UNSUPPORTED"):
        normalize_agent_handoff_artifact(_payload(contract="wrong_contract"))


def test_wrong_schema_version_fails_closed():
    with pytest.raises(AgentHandoffValidationError, match="SCHEMA_VERSION_UNSUPPORTED"):
        normalize_agent_handoff_artifact(_payload(schema_version=999))


def test_unknown_role_fails_closed():
    with pytest.raises(AgentHandoffValidationError, match="ROLE_ID_UNKNOWN"):
        normalize_agent_handoff_artifact(_payload(role_id="scrum_master"))


def test_unknown_workflow_state_fails_closed():
    with pytest.raises(AgentHandoffValidationError, match="WORKFLOW_STATE_UNKNOWN"):
        normalize_agent_handoff_artifact(_payload(workflow_state="MADE_UP_STATE"))


def test_unknown_target_state_fails_closed():
    with pytest.raises(AgentHandoffValidationError, match="WORKFLOW_STATE_UNKNOWN"):
        normalize_agent_handoff_artifact(_payload(target_state="MADE_UP_STATE"))


def test_unknown_verdict_fails_closed():
    with pytest.raises(AgentHandoffValidationError, match="VERDICT_UNKNOWN"):
        normalize_agent_handoff_artifact(_payload(verdict="MAYBE"))


def test_safe_flags_must_be_object():
    with pytest.raises(AgentHandoffValidationError, match="SAFE_FLAGS_MUST_BE_OBJECT"):
        normalize_agent_handoff_artifact(_payload(safe_flags=[]))


def test_unsafe_order_flag_fails_closed():
    safe_flags = dict(REQUIRED_SAFE_FLAGS)
    safe_flags["is_order_action"] = True

    with pytest.raises(AgentHandoffValidationError, match="SAFE_FLAG_IS_ORDER_ACTION_INVALID"):
        normalize_agent_handoff_artifact(_payload(safe_flags=safe_flags))


def test_broker_flag_fails_closed():
    safe_flags = dict(REQUIRED_SAFE_FLAGS)
    safe_flags["broker_api_called"] = True

    with pytest.raises(AgentHandoffValidationError, match="SAFE_FLAG_BROKER_API_CALLED_INVALID"):
        normalize_agent_handoff_artifact(_payload(safe_flags=safe_flags))


def test_live_flag_fails_closed():
    safe_flags = dict(REQUIRED_SAFE_FLAGS)
    safe_flags["live_mode_touched"] = True

    with pytest.raises(AgentHandoffValidationError, match="SAFE_FLAG_LIVE_MODE_TOUCHED_INVALID"):
        normalize_agent_handoff_artifact(_payload(safe_flags=safe_flags))


def test_runtime_wiring_flag_fails_closed():
    safe_flags = dict(REQUIRED_SAFE_FLAGS)
    safe_flags["allowed_for_runtime_wiring"] = True

    with pytest.raises(AgentHandoffValidationError, match="SAFE_FLAG_ALLOWED_FOR_RUNTIME_WIRING_INVALID"):
        normalize_agent_handoff_artifact(_payload(safe_flags=safe_flags))


def test_role_required_outputs_must_be_present():
    payload = _payload(required_outputs=["architecture_decision"])

    with pytest.raises(AgentHandoffValidationError, match="ROLE_REQUIRED_OUTPUTS_MISSING"):
        normalize_agent_handoff_artifact(payload)


def test_rejected_verdict_requires_blockers():
    with pytest.raises(AgentHandoffValidationError, match="BLOCKING_VERDICT_REQUIRES_BLOCKERS"):
        normalize_agent_handoff_artifact(_payload(verdict="REJECTED", blockers=[]))


def test_rejected_verdict_with_blockers_is_valid():
    artifact = normalize_agent_handoff_artifact(_payload(verdict="REJECTED", blockers=["scope drift"]))

    assert artifact.verdict == "REJECTED"
    assert artifact.blockers == ("scope drift",)


def test_list_fields_require_lists():
    with pytest.raises(AgentHandoffValidationError, match="FILES_ALLOWED_MUST_BE_LIST"):
        normalize_agent_handoff_artifact(_payload(files_allowed="docs/"))


def test_list_items_must_be_strings():
    with pytest.raises(AgentHandoffValidationError, match="RISKS_FOUND_ITEM_MUST_BE_STRING"):
        normalize_agent_handoff_artifact(_payload(risks_found=[123]))


def test_required_lists_cannot_be_empty():
    with pytest.raises(AgentHandoffValidationError, match="TESTS_REQUIRED_MISSING"):
        normalize_agent_handoff_artifact(_payload(tests_required=[]))


def test_validate_payload_returns_false_instead_of_raising():
    result = validate_agent_handoff_payload(_payload(role_id="unknown_role"))

    assert result["valid"] is False
    assert result["contract"] == AGENT_HANDOFF_CONTRACT
    assert result["error"] == "ROLE_ID_UNKNOWN"
    assert result["is_order_action"] is False
    assert result["broker_api_called"] is False
    assert result["live_mode_touched"] is False
    assert result["allowed_for_live_execution"] is False
    assert result["real_order_id"] is None


def test_validate_payload_returns_true_for_valid_payload():
    result = validate_agent_handoff_payload(_payload())

    assert result == {
        "contract": AGENT_HANDOFF_CONTRACT,
        "valid": True,
        "task_id": "AGENT-PR13",
        "role_id": "hermes_architect",
        "workflow_state": "REVIEWED_BY_GRILL",
        "target_state": "DESIGNED_BY_HERMES",
        "verdict": "APPROVED",
        **REQUIRED_SAFE_FLAGS,
    }


def test_build_minimal_handoff_payload_includes_role_required_outputs():
    payload = build_minimal_handoff_payload(
        task_id="AGENT-PR13",
        role_id="gsd_implementer",
        workflow_state="DESIGNED_BY_HERMES",
        target_state="IMPLEMENTED_BY_GSD",
    )

    assert "patch_summary" in payload["required_outputs"]
    assert "changed_files" in payload["required_outputs"]
    assert payload["safe_flags"] == REQUIRED_SAFE_FLAGS
    assert normalize_agent_handoff_artifact(payload).role_id == "gsd_implementer"

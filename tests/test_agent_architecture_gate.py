import json
from pathlib import Path

import pytest

from agent_system.architecture_gate import (
    AGENT_ARCHITECTURE_GATE_CONTRACT,
    agent_architecture_gate_schema_contract,
    resolve_agent_task_id,
    run_agent_architecture_gate,
)
from agent_system.handoff_contract import REQUIRED_SAFE_FLAGS, build_minimal_handoff_payload
from agent_system.handoff_validator import DEFAULT_REQUIRED_HANDOFF_ROLES, ROLE_FILE_SUFFIXES


def _write_handoff(root: Path, task_id: str, role_id: str, workflow_state: str, target_state: str, **overrides):
    payload = build_minimal_handoff_payload(
        task_id=task_id,
        role_id=role_id,
        workflow_state=workflow_state,
        target_state=target_state,
    )
    payload.update(overrides)
    path = root / f"{task_id}-{ROLE_FILE_SUFFIXES[role_id]}.md"
    path.write_text(
        "# Handoff\n\n```json\n"
        + json.dumps(payload, indent=2, sort_keys=True)
        + "\n```\n",
        encoding="utf-8",
    )
    return path


def _write_all_required(root: Path, task_id: str):
    root.mkdir(parents=True, exist_ok=True)
    _write_handoff(root, task_id, "scope_owner", "REQUESTED", "SCOPED_BY_SCOPE_OWNER")
    _write_handoff(root, task_id, "grill_reviewer", "SCOPED_BY_SCOPE_OWNER", "REVIEWED_BY_GRILL")
    _write_handoff(root, task_id, "hermes_architect", "REVIEWED_BY_GRILL", "DESIGNED_BY_HERMES")
    _write_handoff(root, task_id, "gsd_implementer", "DESIGNED_BY_HERMES", "IMPLEMENTED_BY_GSD")
    _write_handoff(root, task_id, "qa_safety_reviewer", "IMPLEMENTED_BY_GSD", "REVIEWED_BY_QA_SAFETY")
    _write_handoff(root, task_id, "evidence_recorder", "REVIEWED_BY_QA_SAFETY", "EVIDENCE_RECORDED")


def test_schema_contract_exposes_ci_gate_scope_and_safe_flags():
    contract = agent_architecture_gate_schema_contract()

    assert contract["contract"] == AGENT_ARCHITECTURE_GATE_CONTRACT
    assert contract["required_checks"] == [
        "role_registry_valid",
        "workflow_state_valid",
        "handoff_contract_present",
        "handoff_evidence_valid",
    ]
    assert contract["required_safe_flags"] == REQUIRED_SAFE_FLAGS
    assert contract["scope"] == "ci_architecture_gate_only_no_changed_file_audit_no_pr_template_no_execution"


@pytest.mark.parametrize(
    ("task_ref", "expected"),
    [
        ("AGENT-PR15", "AGENT-PR15"),
        ("agent-pr15", "AGENT-PR15"),
        ("Agent PR 15: Add CI Gate", "AGENT-PR15"),
        ("Agent_PR_15", "AGENT-PR15"),
    ],
)
def test_resolve_agent_task_id(task_ref, expected):
    assert resolve_agent_task_id(task_ref) == expected


def test_resolve_agent_task_id_rejects_missing_or_unsafe_values():
    with pytest.raises(ValueError, match="TASK_REF_MISSING"):
        resolve_agent_task_id(" ")
    with pytest.raises(ValueError, match="TASK_REF_UNSAFE"):
        resolve_agent_task_id("../AGENT-PR15")
    with pytest.raises(ValueError, match="TASK_REF_CANNOT_RESOLVE_AGENT_TASK_ID"):
        resolve_agent_task_id("regular feature PR")


def test_gate_passes_when_contracts_and_handoffs_are_valid(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR15")

    report = run_agent_architecture_gate(task_ref="Agent PR 15", handoff_dir=tmp_path)

    assert report.valid is True
    assert report.task_id == "AGENT-PR15"
    assert report.blockers == ()
    assert report.role_registry_valid is True
    assert report.workflow_state_valid is True
    assert report.handoff_contract_present is True
    assert report.handoff_evidence_valid is True
    assert report.handoff_roles_found == tuple(sorted(DEFAULT_REQUIRED_HANDOFF_ROLES))
    assert report.handoff_missing_roles == ()
    assert report.read_only is True
    assert report.is_order_action is False
    assert report.broker_api_called is False
    assert report.live_mode_touched is False
    assert report.allowed_for_live_execution is False
    assert report.real_order_id is None
    assert report.allowed_for_runtime_wiring is False
    assert report.allowed_for_broker_api is False


def test_gate_fails_when_handoff_evidence_is_missing(tmp_path):
    report = run_agent_architecture_gate(task_ref="AGENT-PR15", handoff_dir=tmp_path)

    assert report.valid is False
    assert "HANDOFF_EVIDENCE:HANDOFF_FILE_MISSING" in report.blockers
    assert "HANDOFF_EVIDENCE:HANDOFF_REQUIRED_ROLE_MISSING" in report.blockers
    assert set(report.handoff_missing_roles) == set(DEFAULT_REQUIRED_HANDOFF_ROLES)


def test_gate_fails_when_one_handoff_payload_is_invalid(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR15")
    bad_flags = dict(REQUIRED_SAFE_FLAGS)
    bad_flags["broker_api_called"] = True
    _write_handoff(
        tmp_path,
        "AGENT-PR15",
        "hermes_architect",
        "REVIEWED_BY_GRILL",
        "DESIGNED_BY_HERMES",
        safe_flags=bad_flags,
    )

    report = run_agent_architecture_gate(task_ref="AGENT-PR15", handoff_dir=tmp_path)

    assert report.valid is False
    assert "HANDOFF_EVIDENCE:HANDOFF_FILE_INVALID" in report.blockers
    assert report.handoff_evidence_valid is False


def test_gate_report_to_dict_is_json_safe(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR15")
    payload = run_agent_architecture_gate(task_ref="AGENT-PR15", handoff_dir=tmp_path).to_dict()
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["contract"] == AGENT_ARCHITECTURE_GATE_CONTRACT
    assert payload["valid"] is True
    assert "AGENT-PR15" in rendered
    assert payload["metadata"]["scope"] == "ci_architecture_gate_only_no_changed_file_audit_no_pr_template_no_execution"

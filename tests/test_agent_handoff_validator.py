import json
from pathlib import Path

import pytest

from agent_system.handoff_contract import REQUIRED_SAFE_FLAGS, build_minimal_handoff_payload
from agent_system.handoff_validator import (
    AGENT_HANDOFF_VALIDATOR_CONTRACT,
    DEFAULT_REQUIRED_HANDOFF_ROLES,
    ROLE_FILE_SUFFIXES,
    agent_handoff_validator_schema_contract,
    expected_handoff_paths,
    extract_handoff_payload_from_markdown,
    load_handoff_artifact,
    report_to_json,
    validate_handoff_evidence,
)


def _write_handoff(
    root: Path,
    file_task_id: str,
    file_role_id: str,
    workflow_state: str,
    target_state: str,
    **payload_overrides,
):
    payload = build_minimal_handoff_payload(
        task_id=file_task_id,
        role_id=file_role_id,
        workflow_state=workflow_state,
        target_state=target_state,
    )
    payload.update(payload_overrides)
    path = root / f"{file_task_id}-{ROLE_FILE_SUFFIXES[file_role_id]}.md"
    path.write_text(
        "# Handoff\n\n"
        "```json\n"
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


def test_schema_contract_exposes_required_roles_and_safe_flags():
    contract = agent_handoff_validator_schema_contract()

    assert contract["contract"] == AGENT_HANDOFF_VALIDATOR_CONTRACT
    assert contract["required_roles"] == list(DEFAULT_REQUIRED_HANDOFF_ROLES)
    assert contract["role_file_suffixes"]["qa_safety_reviewer"] == "qa-safety"
    assert contract["required_safe_flags"] == REQUIRED_SAFE_FLAGS
    assert contract["payload_contract"] == "agent_role_handoff_artifact_v1"
    assert contract["scope"] == "handoff_evidence_validator_only_no_ci_no_changed_file_audit_no_execution"


def test_expected_handoff_paths_are_deterministic(tmp_path):
    paths = expected_handoff_paths("AGENT-PR14", tmp_path)

    assert paths["scope_owner"] == tmp_path / "AGENT-PR14-scope-owner.md"
    assert paths["grill_reviewer"] == tmp_path / "AGENT-PR14-grill.md"
    assert paths["qa_safety_reviewer"] == tmp_path / "AGENT-PR14-qa-safety.md"
    assert paths["evidence_recorder"] == tmp_path / "AGENT-PR14-evidence.md"


def test_validate_all_required_handoff_files_passes(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR14")

    report = validate_handoff_evidence(task_id="AGENT-PR14", handoff_dir=tmp_path)

    assert report.valid is True
    assert report.task_id == "AGENT-PR14"
    assert report.blockers == ()
    assert report.missing_roles == ()
    assert report.missing_files == ()
    assert report.roles_found == tuple(sorted(DEFAULT_REQUIRED_HANDOFF_ROLES))
    assert all(result.valid for result in report.file_results)
    assert report.read_only is True
    assert report.is_order_action is False
    assert report.broker_api_called is False
    assert report.live_mode_touched is False
    assert report.allowed_for_live_execution is False
    assert report.real_order_id is None


def test_validate_detects_missing_file_and_role(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR14")
    (tmp_path / "AGENT-PR14-evidence.md").unlink()

    report = validate_handoff_evidence(task_id="AGENT-PR14", handoff_dir=tmp_path)

    assert report.valid is False
    assert "HANDOFF_FILE_MISSING" in report.blockers
    assert "HANDOFF_REQUIRED_ROLE_MISSING" in report.blockers
    assert report.missing_roles == ("evidence_recorder",)
    assert str(tmp_path / "AGENT-PR14-evidence.md") in report.missing_files


def test_validate_detects_invalid_payload(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR14")
    bad_flags = dict(REQUIRED_SAFE_FLAGS)
    bad_flags["live_mode_touched"] = True
    _write_handoff(
        tmp_path,
        "AGENT-PR14",
        "hermes_architect",
        "REVIEWED_BY_GRILL",
        "DESIGNED_BY_HERMES",
        safe_flags=bad_flags,
    )

    report = validate_handoff_evidence(task_id="AGENT-PR14", handoff_dir=tmp_path)

    assert report.valid is False
    assert "HANDOFF_FILE_INVALID" in report.blockers
    hermes_result = next(result for result in report.file_results if result.path.endswith("AGENT-PR14-hermes.md"))
    assert hermes_result.valid is False
    assert hermes_result.error == "SAFE_FLAG_LIVE_MODE_TOUCHED_INVALID"


def test_validate_detects_task_id_mismatch(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR14")
    _write_handoff(
        tmp_path,
        "AGENT-PR14",
        "gsd_implementer",
        "DESIGNED_BY_HERMES",
        "IMPLEMENTED_BY_GSD",
        task_id="OTHER-TASK",
    )

    report = validate_handoff_evidence(task_id="AGENT-PR14", handoff_dir=tmp_path)

    assert report.valid is False
    assert "HANDOFF_TASK_ID_MISMATCH" in report.blockers
    gsd_result = next(result for result in report.file_results if result.path.endswith("AGENT-PR14-gsd.md"))
    assert gsd_result.error == "HANDOFF_TASK_ID_MISMATCH"


def test_validate_detects_role_id_mismatch(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR14")
    _write_handoff(
        tmp_path,
        "AGENT-PR14",
        "gsd_implementer",
        "DESIGNED_BY_HERMES",
        "IMPLEMENTED_BY_GSD",
        role_id="hermes_architect",
    )

    report = validate_handoff_evidence(task_id="AGENT-PR14", handoff_dir=tmp_path)

    assert report.valid is False
    assert "HANDOFF_ROLE_ID_MISMATCH" in report.blockers
    gsd_result = next(result for result in report.file_results if result.path.endswith("AGENT-PR14-gsd.md"))
    assert gsd_result.error == "HANDOFF_ROLE_ID_MISMATCH"


def test_extract_handoff_payload_ignores_non_contract_json_blocks():
    payload = build_minimal_handoff_payload(
        task_id="AGENT-PR14",
        role_id="scope_owner",
        workflow_state="REQUESTED",
        target_state="SCOPED_BY_SCOPE_OWNER",
    )
    markdown = (
        "```json\n{\"contract\": \"not_it\"}\n```\n\n"
        "```json\n" + json.dumps(payload) + "\n```\n"
    )

    extracted = extract_handoff_payload_from_markdown(markdown)

    assert extracted["contract"] == "agent_role_handoff_artifact_v1"
    assert extracted["role_id"] == "scope_owner"


def test_load_handoff_artifact_requires_json_payload(tmp_path):
    path = tmp_path / "AGENT-PR14-grill.md"
    path.write_text("# No JSON here\n", encoding="utf-8")

    with pytest.raises(Exception, match="HANDOFF_JSON_PAYLOAD_NOT_FOUND"):
        load_handoff_artifact(path)


def test_task_id_rejects_unsafe_path_values(tmp_path):
    with pytest.raises(ValueError, match="TASK_ID_UNSAFE"):
        validate_handoff_evidence(task_id="../AGENT-PR14", handoff_dir=tmp_path)


def test_required_roles_reject_unknown_role(tmp_path):
    with pytest.raises(ValueError, match="UNKNOWN_REQUIRED_HANDOFF_ROLE"):
        validate_handoff_evidence(task_id="AGENT-PR14", handoff_dir=tmp_path, required_roles=["scrum_master"])


def test_report_to_dict_and_json_are_stable(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR14")
    report = validate_handoff_evidence(task_id="AGENT-PR14", handoff_dir=tmp_path)
    payload = report.to_dict()
    rendered = report_to_json(report)

    assert payload["valid"] is True
    assert isinstance(payload["file_results"], list)
    assert "AGENT-PR14" in rendered
    assert "agent_handoff_evidence_validator_v1" in rendered


def test_validate_can_use_subset_of_required_roles(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    _write_handoff(tmp_path, "AGENT-PR14", "grill_reviewer", "SCOPED_BY_SCOPE_OWNER", "REVIEWED_BY_GRILL")

    report = validate_handoff_evidence(
        task_id="AGENT-PR14",
        handoff_dir=tmp_path,
        required_roles=["grill_reviewer"],
    )

    assert report.valid is True
    assert report.roles_found == ("grill_reviewer",)
    assert report.required_roles == ("grill_reviewer",)

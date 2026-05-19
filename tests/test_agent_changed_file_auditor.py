import json
from pathlib import Path

from agent_system.changed_file_auditor import (
    AGENT_CHANGED_FILE_AUDITOR_CONTRACT,
    agent_changed_file_auditor_schema_contract,
    audit_changed_files_against_handoffs,
    normalize_changed_file_path,
    path_matches_rule,
)
from agent_system.handoff_contract import REQUIRED_SAFE_FLAGS, build_minimal_handoff_payload
from agent_system.handoff_validator import ROLE_FILE_SUFFIXES


def _write_scope_handoff(root: Path, task_id: str, role_id: str, files_allowed, files_forbidden=None):
    states = {
        "scope_owner": ("REQUESTED", "SCOPED_BY_SCOPE_OWNER"),
        "hermes_architect": ("REVIEWED_BY_GRILL", "DESIGNED_BY_HERMES"),
        "gsd_implementer": ("DESIGNED_BY_HERMES", "IMPLEMENTED_BY_GSD"),
    }
    workflow_state, target_state = states[role_id]
    payload = build_minimal_handoff_payload(
        task_id=task_id,
        role_id=role_id,
        workflow_state=workflow_state,
        target_state=target_state,
    )
    payload["files_allowed"] = list(files_allowed)
    payload["files_forbidden"] = list(files_forbidden or ["broker_contract/", "run_live.sh", "api/"])
    path = root / f"{task_id}-{ROLE_FILE_SUFFIXES[role_id]}.md"
    path.write_text(
        "# Handoff\n\n```json\n"
        + json.dumps(payload, indent=2, sort_keys=True)
        + "\n```\n",
        encoding="utf-8",
    )
    return path


def _write_scope_set(root: Path, task_id: str, files_allowed=None, files_forbidden=None):
    root.mkdir(parents=True, exist_ok=True)
    allowed = files_allowed or ["agent_system/", "tests/", "docs/", "scripts/"]
    for role in ("scope_owner", "hermes_architect", "gsd_implementer"):
        _write_scope_handoff(root, task_id, role, allowed, files_forbidden=files_forbidden)


def test_schema_contract_exposes_scope_and_safe_flags():
    contract = agent_changed_file_auditor_schema_contract()

    assert contract["contract"] == AGENT_CHANGED_FILE_AUDITOR_CONTRACT
    assert contract["default_scope_roles"] == ["scope_owner", "hermes_architect", "gsd_implementer"]
    assert contract["required_safe_flags"] == REQUIRED_SAFE_FLAGS
    assert contract["scope"] == "changed_file_scope_auditor_only_no_pr_template_no_architecture_report_no_execution"


def test_path_normalization_and_rule_matching():
    assert normalize_changed_file_path("./agent_system/changed_file_auditor.py") == "agent_system/changed_file_auditor.py"
    assert path_matches_rule("agent_system/changed_file_auditor.py", "agent_system/") is True
    assert path_matches_rule("agent_system/changed_file_auditor.py", "agent_system/changed_file_auditor.py") is True
    assert path_matches_rule("agent_system_extra/file.py", "agent_system/") is False


def test_audit_accepts_files_allowed_by_all_scope_roles_with_human_approval(tmp_path):
    _write_scope_set(tmp_path, "AGENT-PR16")

    report = audit_changed_files_against_handoffs(
        task_id="AGENT-PR16",
        changed_files=[
            "agent_system/changed_file_auditor.py",
            "tests/test_agent_changed_file_auditor.py",
            "docs/agent-changed-file-scope-auditor.md",
            "scripts/audit_agent_changed_files.py",
        ],
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is True
    assert report.blockers == ()
    assert len(report.findings) == 4
    assert all(finding.accepted for finding in report.findings)
    assert report.read_only is True
    assert report.is_order_action is False
    assert report.broker_api_called is False
    assert report.live_mode_touched is False
    assert report.allowed_for_live_execution is False
    assert report.real_order_id is None


def test_audit_blocks_file_outside_approved_scope(tmp_path):
    _write_scope_set(tmp_path, "AGENT-PR16", files_allowed=["docs/"])

    report = audit_changed_files_against_handoffs(
        task_id="AGENT-PR16",
        changed_files=["agent_system/changed_file_auditor.py"],
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is False
    assert "CHANGED_FILE_OUTSIDE_APPROVED_SCOPE" in report.blockers
    assert report.findings[0].accepted is False
    assert report.findings[0].matched_allowed_roles == ()


def test_audit_blocks_file_forbidden_by_any_handoff(tmp_path):
    _write_scope_set(tmp_path, "AGENT-PR16", files_allowed=["broker_contract/"], files_forbidden=["broker_contract/"])

    report = audit_changed_files_against_handoffs(
        task_id="AGENT-PR16",
        changed_files=["broker_contract/client.py"],
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is False
    assert "CHANGED_FILE_FORBIDDEN_BY_HANDOFF" in report.blockers
    assert report.findings[0].matched_forbidden_roles == ("gsd_implementer", "hermes_architect", "scope_owner")


def test_audit_blocks_high_risk_path_without_human_approval(tmp_path):
    _write_scope_set(tmp_path, "AGENT-PR16", files_allowed=["agent_system/"])

    report = audit_changed_files_against_handoffs(
        task_id="AGENT-PR16",
        changed_files=["agent_system/changed_file_auditor.py"],
        handoff_dir=tmp_path,
        human_approved=False,
    )

    assert report.valid is False
    assert "HIGH_RISK_PATH_REQUIRES_HUMAN_APPROVAL" in report.blockers
    assert report.findings[0].high_risk is True


def test_audit_allows_high_risk_path_with_human_approval(tmp_path):
    _write_scope_set(tmp_path, "AGENT-PR16", files_allowed=["agent_system/"])

    report = audit_changed_files_against_handoffs(
        task_id="AGENT-PR16",
        changed_files=["agent_system/changed_file_auditor.py"],
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is True
    assert report.findings[0].accepted is True
    assert report.findings[0].high_risk is True


def test_audit_fails_closed_on_missing_changed_files(tmp_path):
    _write_scope_set(tmp_path, "AGENT-PR16")

    report = audit_changed_files_against_handoffs(
        task_id="AGENT-PR16",
        changed_files=[],
        handoff_dir=tmp_path,
    )

    assert report.valid is False
    assert report.blockers == ("CHANGED_FILES_MISSING",)


def test_audit_fails_closed_on_unsafe_changed_file_path(tmp_path):
    _write_scope_set(tmp_path, "AGENT-PR16")

    report = audit_changed_files_against_handoffs(
        task_id="AGENT-PR16",
        changed_files=["../secrets.env"],
        handoff_dir=tmp_path,
    )

    assert report.valid is False
    assert report.blockers == ("CHANGED_FILE_PATH_UNSAFE",)


def test_audit_fails_closed_when_scope_handoff_missing(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    _write_scope_handoff(tmp_path, "AGENT-PR16", "scope_owner", ["docs/"])

    report = audit_changed_files_against_handoffs(
        task_id="AGENT-PR16",
        changed_files=["docs/example.md"],
        handoff_dir=tmp_path,
    )

    assert report.valid is False
    assert "HANDOFF_SCOPE_EVIDENCE_INVALID" in report.blockers
    assert "HANDOFF_FILE_MISSING" in report.blockers


def test_audit_report_to_dict_is_json_safe(tmp_path):
    _write_scope_set(tmp_path, "AGENT-PR16")
    report = audit_changed_files_against_handoffs(
        task_id="AGENT-PR16",
        changed_files=["docs/example.md"],
        handoff_dir=tmp_path,
        human_approved=True,
    )
    payload = report.to_dict()
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["contract"] == AGENT_CHANGED_FILE_AUDITOR_CONTRACT
    assert isinstance(payload["findings"], list)
    assert "AGENT-PR16" in rendered


def test_unknown_scope_role_fails_closed(tmp_path):
    _write_scope_set(tmp_path, "AGENT-PR16")

    try:
        audit_changed_files_against_handoffs(
            task_id="AGENT-PR16",
            changed_files=["docs/example.md"],
            handoff_dir=tmp_path,
            scope_roles=["scrum_master"],
        )
    except ValueError as exc:
        assert str(exc) == "UNKNOWN_SCOPE_ROLE:scrum_master"
    else:
        raise AssertionError("expected unknown scope role to fail closed")

import json
from pathlib import Path

from agent_system.handoff_contract import build_minimal_handoff_payload
from agent_system.handoff_validator import ROLE_FILE_SUFFIXES
from agent_system.pr_gate import (
    AGENT_PR_GATE_CONTRACT,
    REQUIRED_PR_BODY_PHRASES,
    REQUIRED_PR_BODY_SECTIONS,
    agent_pr_gate_schema_contract,
    extract_changed_files_from_diff_name_output,
    extract_markdown_codeblock_paths,
    run_agent_pr_gate,
    validate_pr_body_template,
)


def _write_handoff(root: Path, task_id: str, role_id: str, workflow_state: str, target_state: str, files_allowed=None, files_forbidden=None):
    payload = build_minimal_handoff_payload(
        task_id=task_id,
        role_id=role_id,
        workflow_state=workflow_state,
        target_state=target_state,
    )
    payload["files_allowed"] = list(files_allowed or ["agent_system/", "scripts/", "tests/", "docs/", ".github/workflows/", "PROJECT_STATE.md"])
    payload["files_forbidden"] = list(files_forbidden or ["api/", "frontend/", "dashboard/", "main.py", "run_live.sh", "runtime_contract.py"])
    path = root / f"{task_id}-{ROLE_FILE_SUFFIXES[role_id]}.md"
    path.write_text("# Handoff\n\n```json\n" + json.dumps(payload, indent=2, sort_keys=True) + "\n```\n", encoding="utf-8")


def _write_all_required(root: Path, task_id: str):
    root.mkdir(parents=True, exist_ok=True)
    _write_handoff(root, task_id, "scope_owner", "REQUESTED", "SCOPED_BY_SCOPE_OWNER")
    _write_handoff(root, task_id, "grill_reviewer", "SCOPED_BY_SCOPE_OWNER", "REVIEWED_BY_GRILL")
    _write_handoff(root, task_id, "hermes_architect", "REVIEWED_BY_GRILL", "DESIGNED_BY_HERMES")
    _write_handoff(root, task_id, "gsd_implementer", "DESIGNED_BY_HERMES", "IMPLEMENTED_BY_GSD")
    _write_handoff(root, task_id, "qa_safety_reviewer", "IMPLEMENTED_BY_GSD", "REVIEWED_BY_QA_SAFETY")
    _write_handoff(root, task_id, "evidence_recorder", "REVIEWED_BY_QA_SAFETY", "EVIDENCE_RECORDED")


def _valid_body():
    sections = "\n".join(f"{section}\ncontent" for section in REQUIRED_PR_BODY_SECTIONS)
    phrases = "\n".join(REQUIRED_PR_BODY_PHRASES)
    return sections + "\n" + phrases + "\n"


def test_schema_contract_exposes_required_template_and_safe_flags():
    contract = agent_pr_gate_schema_contract()

    assert contract["contract"] == AGENT_PR_GATE_CONTRACT
    assert contract["required_sections"] == list(REQUIRED_PR_BODY_SECTIONS)
    assert contract["required_phrases"] == list(REQUIRED_PR_BODY_PHRASES)
    assert contract["required_checks"] == ["pr_body_valid", "architecture_gate_valid", "changed_file_audit_valid"]
    assert contract["required_safe_flags"]["read_only"] is True
    assert contract["scope"] == "pr_template_local_developer_gate_only_no_architecture_replay_report_no_execution"


def test_pr_body_template_passes_when_required_sections_and_phrases_exist():
    report = validate_pr_body_template(_valid_body())

    assert report.valid is True
    assert report.missing_sections == ()
    assert report.missing_phrases == ()


def test_pr_body_template_fails_when_required_parts_missing():
    report = validate_pr_body_template("## Summary\nOnly summary")

    assert report.valid is False
    assert "## Agent handoff evidence" in report.missing_sections
    assert "Grill independent: yes" in report.missing_phrases


def test_local_gate_passes_when_body_architecture_and_changed_files_are_valid(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR17")

    report = run_agent_pr_gate(
        task_ref="Agent PR 17: Add PR Template and Local Developer Gate",
        changed_files=[
            "agent_system/pr_gate.py",
            "scripts/agent_pr_gate.py",
            "tests/test_agent_pr_gate.py",
            "docs/agent-pr-developer-gate.md",
        ],
        pr_body=_valid_body(),
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is True
    assert report.blockers == ()
    assert report.pr_body_valid is True
    assert report.architecture_gate_valid is True
    assert report.changed_file_audit_valid is True
    assert report.changed_file_count == 4
    assert report.read_only is True
    assert report.is_order_action is False
    assert report.broker_api_called is False
    assert report.live_mode_touched is False
    assert report.allowed_for_live_execution is False
    assert report.real_order_id is None


def test_local_gate_blocks_invalid_pr_body(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR17")

    report = run_agent_pr_gate(
        task_ref="AGENT-PR17",
        changed_files=["docs/agent-pr-developer-gate.md"],
        pr_body="## Summary\nIncomplete",
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is False
    assert "PR_BODY_TEMPLATE_INVALID" in report.blockers
    assert report.pr_body_valid is False


def test_local_gate_blocks_missing_handoff_evidence(tmp_path):
    report = run_agent_pr_gate(
        task_ref="AGENT-PR17",
        changed_files=["docs/agent-pr-developer-gate.md"],
        pr_body=_valid_body(),
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is False
    assert any(blocker.startswith("ARCHITECTURE_GATE:HANDOFF_EVIDENCE") for blocker in report.blockers)
    assert any(blocker.startswith("CHANGED_FILE_AUDIT:HANDOFF_SCOPE_EVIDENCE_INVALID") for blocker in report.blockers)


def test_local_gate_blocks_changed_file_outside_scope(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR17")

    report = run_agent_pr_gate(
        task_ref="AGENT-PR17",
        changed_files=["api/server.py"],
        pr_body=_valid_body(),
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is False
    assert "CHANGED_FILE_AUDIT:CHANGED_FILE_FORBIDDEN_BY_HANDOFF" in report.blockers
    assert report.changed_file_audit_valid is False


def test_extract_changed_files_from_diff_name_output_ignores_comments_and_blanks():
    assert extract_changed_files_from_diff_name_output("\n# comment\ndocs/a.md\n\nagent_system/x.py\n") == (
        "docs/a.md",
        "agent_system/x.py",
    )


def test_extract_markdown_codeblock_paths_reads_named_section():
    body = "## Files changed\n```text\ndocs/a.md\nagent_system/x.py\n```\n## Other\n"

    assert extract_markdown_codeblock_paths(body, "## Files changed") == ("docs/a.md", "agent_system/x.py")


def test_report_to_dict_is_json_safe(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR17")
    report = run_agent_pr_gate(
        task_ref="AGENT-PR17",
        changed_files=["docs/agent-pr-developer-gate.md"],
        pr_body=_valid_body(),
        handoff_dir=tmp_path,
        human_approved=True,
    )
    payload = report.to_dict()
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["contract"] == AGENT_PR_GATE_CONTRACT
    assert "AGENT-PR17" in rendered
    assert payload["metadata"]["scope"] == "pr_template_local_developer_gate_only_no_architecture_replay_report_no_execution"

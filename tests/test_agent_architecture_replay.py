import json
from pathlib import Path

from agent_system.architecture_replay import (
    AGENT_ARCHITECTURE_REPLAY_CONTRACT,
    agent_architecture_replay_schema_contract,
    architecture_replay_report_to_json,
    architecture_replay_report_to_markdown,
    run_architecture_replay_report,
)
from agent_system.handoff_contract import build_minimal_handoff_payload
from agent_system.handoff_validator import ROLE_FILE_SUFFIXES
from agent_system.pr_gate import REQUIRED_PR_BODY_PHRASES, REQUIRED_PR_BODY_SECTIONS


def _valid_body():
    sections = "\n".join(f"{section}\ncontent" for section in REQUIRED_PR_BODY_SECTIONS)
    phrases = "\n".join(REQUIRED_PR_BODY_PHRASES)
    return sections + "\n" + phrases + "\n"


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


def test_schema_contract_exposes_replay_sections_and_safe_flags():
    contract = agent_architecture_replay_schema_contract()

    assert contract["contract"] == AGENT_ARCHITECTURE_REPLAY_CONTRACT
    assert contract["sections"] == [
        "role_registry",
        "workflow_state_machine",
        "handoff_evidence",
        "architecture_gate",
        "pr_body_template",
        "changed_file_scope",
    ]
    assert contract["required_safe_flags"]["read_only"] is True
    assert contract["scope"] == "architecture_replay_audit_report_only_no_execution_no_product_behavior"


def test_replay_report_passes_when_all_governance_layers_pass(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR18")

    report = run_architecture_replay_report(
        task_ref="Agent PR 18: Architecture Replay / Audit Report",
        changed_files=[
            "agent_system/architecture_replay.py",
            "scripts/architecture_replay_report.py",
            "tests/test_agent_architecture_replay.py",
            "docs/agent-architecture-replay-report.md",
        ],
        pr_body=_valid_body(),
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is True
    assert report.blockers == ()
    assert [section.name for section in report.sections] == [
        "role_registry",
        "workflow_state_machine",
        "handoff_evidence",
        "architecture_gate",
        "pr_body_template",
        "changed_file_scope",
    ]
    assert all(section.valid for section in report.sections)
    assert report.read_only is True
    assert report.is_order_action is False
    assert report.broker_api_called is False
    assert report.live_mode_touched is False
    assert report.allowed_for_live_execution is False
    assert report.real_order_id is None


def test_replay_report_fails_when_handoff_evidence_missing(tmp_path):
    report = run_architecture_replay_report(
        task_ref="AGENT-PR18",
        changed_files=["docs/agent-architecture-replay-report.md"],
        pr_body=_valid_body(),
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is False
    assert any(blocker.startswith("handoff_evidence:") for blocker in report.blockers)
    assert any(blocker.startswith("architecture_gate:HANDOFF_EVIDENCE") for blocker in report.blockers)
    assert any(blocker.startswith("changed_file_scope:HANDOFF_SCOPE_EVIDENCE_INVALID") for blocker in report.blockers)


def test_replay_report_fails_when_pr_body_missing_required_content(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR18")

    report = run_architecture_replay_report(
        task_ref="AGENT-PR18",
        changed_files=["docs/agent-architecture-replay-report.md"],
        pr_body="## Summary\nIncomplete",
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is False
    assert any(blocker.startswith("pr_body_template:") for blocker in report.blockers)


def test_replay_report_fails_when_changed_file_scope_fails(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR18")

    report = run_architecture_replay_report(
        task_ref="AGENT-PR18",
        changed_files=["api/server.py"],
        pr_body=_valid_body(),
        handoff_dir=tmp_path,
        human_approved=True,
    )

    assert report.valid is False
    assert "changed_file_scope:CHANGED_FILE_FORBIDDEN_BY_HANDOFF" in report.blockers


def test_report_json_and_markdown_renderers_are_stable(tmp_path):
    _write_all_required(tmp_path, "AGENT-PR18")
    report = run_architecture_replay_report(
        task_ref="AGENT-PR18",
        changed_files=["docs/agent-architecture-replay-report.md"],
        pr_body=_valid_body(),
        handoff_dir=tmp_path,
        human_approved=True,
    )

    rendered_json = architecture_replay_report_to_json(report)
    rendered_markdown = architecture_replay_report_to_markdown(report)
    payload = json.loads(rendered_json)

    assert payload["contract"] == AGENT_ARCHITECTURE_REPLAY_CONTRACT
    assert "Architecture Replay Audit Report" in rendered_markdown
    assert "Overall status" in rendered_markdown
    assert "Safe flags" in rendered_markdown

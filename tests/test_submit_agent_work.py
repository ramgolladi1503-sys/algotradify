from __future__ import annotations

import json
from pathlib import Path

from scripts.submit_agent_work import (
    EXIT_APPROVED,
    EXIT_BLOCKED,
    EXIT_REJECTED,
    run_agent_work_submission,
)


def _payload(**overrides):
    payload = {
        "schema_version": 1,
        "source_agent": "gsd",
        "action": "GENERATE_TESTS",
        "title": "Add local CLI tests",
        "scope": "Add deterministic tests for the local agent work CLI.",
        "allowed_paths": ["tests/"],
        "requested_paths": ["tests/test_submit_agent_work.py"],
        "forbidden_paths": [".env", "credentials.py", "broker_contract/", "runtime/live"],
        "requires_human_approval": False,
        "metadata": {"project": "algotradify"},
    }
    payload.update(overrides)
    return payload


def _write_payload(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "payload.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_missing_payload_file_exits_blocked(tmp_path):
    result = run_agent_work_submission(
        payload_path=tmp_path / "missing.json",
        evidence_root=tmp_path / "evidence",
    )

    assert result.exit_code == EXIT_BLOCKED
    assert result.status == "INPUT_ERROR"
    assert result.payload["read_only"] is True
    assert result.payload["is_order_action"] is False
    assert result.payload["broker_api_called"] is False
    assert result.payload["live_mode_touched"] is False
    assert result.payload["allowed_for_live_execution"] is False


def test_malformed_json_exits_blocked(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")

    result = run_agent_work_submission(payload_path=path, evidence_root=tmp_path / "evidence")

    assert result.exit_code == EXIT_BLOCKED
    assert result.status == "INPUT_ERROR"
    assert "invalid json" in result.message


def test_non_object_json_exits_blocked(tmp_path):
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    result = run_agent_work_submission(payload_path=path, evidence_root=tmp_path / "evidence")

    assert result.exit_code == EXIT_BLOCKED
    assert result.status == "INPUT_ERROR"
    assert result.payload["broker_api_called"] is False


def test_approved_docs_tests_request_exits_zero_and_writes_evidence(tmp_path):
    payload_path = _write_payload(tmp_path, _payload())
    evidence_root = tmp_path / "evidence"

    result = run_agent_work_submission(payload_path=payload_path, evidence_root=evidence_root)

    assert result.exit_code == EXIT_APPROVED
    assert result.status == "APPROVED_FOR_PATCH"
    assert result.payload["scope_decision"]["state"] == "APPROVED_FOR_PATCH"
    assert result.payload["approval_decision"]["approved"] is True
    assert result.payload["read_only"] is True
    assert result.payload["is_order_action"] is False
    assert result.payload["broker_api_called"] is False
    assert result.payload["live_mode_touched"] is False
    assert result.payload["allowed_for_live_execution"] is False
    assert (evidence_root / "agent_work_latest.json").exists()
    assert list(evidence_root.glob("agent_work_*.jsonl"))


def test_blocked_order_action_exits_blocked_and_writes_rejected_evidence(tmp_path):
    payload_path = _write_payload(tmp_path, _payload(action="PLACE_ORDER"))
    evidence_root = tmp_path / "evidence"

    result = run_agent_work_submission(
        payload_path=payload_path,
        approve=True,
        approved_by="ram",
        evidence_root=evidence_root,
    )

    assert result.exit_code == EXIT_BLOCKED
    assert result.status == "BLOCKED"
    assert result.payload["scope_decision"]["state"] == "BLOCKED"
    assert result.payload["approval_decision"]["approved"] is False
    assert "ORDER_ACTION_FORBIDDEN" in result.payload["scope_decision"]["blockers"]

    latest = json.loads((evidence_root / "agent_work_latest.json").read_text(encoding="utf-8"))
    assert latest["approval_decision"]["approved"] is False
    assert latest["safety"]["broker_api_called"] is False


def test_human_gated_request_without_approval_exits_rejected(tmp_path):
    payload_path = _write_payload(
        tmp_path,
        _payload(
            action="GENERATE_PATCH",
            allowed_paths=["agent_system/"],
            requested_paths=["agent_system/approval.py"],
        ),
    )

    result = run_agent_work_submission(payload_path=payload_path, evidence_root=tmp_path / "evidence")

    assert result.exit_code == EXIT_REJECTED
    assert result.status == "REJECTED"
    assert result.payload["scope_decision"]["state"] == "WAITING_HUMAN_APPROVAL"
    assert "HUMAN_APPROVAL_REQUIRED" in result.payload["approval_decision"]["blockers"]
    assert result.payload["allowed_for_live_execution"] is False


def test_human_gated_request_with_approval_exits_zero_but_patch_only(tmp_path):
    payload_path = _write_payload(
        tmp_path,
        _payload(
            action="GENERATE_PATCH",
            allowed_paths=["agent_system/"],
            requested_paths=["agent_system/approval.py"],
        ),
    )

    result = run_agent_work_submission(
        payload_path=payload_path,
        approve=True,
        approved_by="ram",
        evidence_root=tmp_path / "evidence",
    )

    assert result.exit_code == EXIT_APPROVED
    assert result.status == "APPROVED_FOR_PATCH"
    assert result.payload["approval_decision"]["approved_by"] == "ram"
    assert result.payload["approval_decision"]["allowed_for_patch"] is True
    assert result.payload["approval_decision"]["allowed_for_runtime_wiring"] is False
    assert result.payload["approval_decision"]["allowed_for_broker_api"] is False
    assert result.payload["approval_decision"]["allowed_for_live_execution"] is False


def test_human_gated_request_with_missing_approved_by_exits_rejected(tmp_path):
    payload_path = _write_payload(
        tmp_path,
        _payload(
            action="GENERATE_PATCH",
            allowed_paths=["agent_system/"],
            requested_paths=["agent_system/approval.py"],
        ),
    )

    result = run_agent_work_submission(
        payload_path=payload_path,
        approve=True,
        approved_by=" ",
        evidence_root=tmp_path / "evidence",
    )

    assert result.exit_code == EXIT_REJECTED
    assert result.status == "REJECTED"
    assert "APPROVED_BY_REQUIRED" in result.payload["approval_decision"]["blockers"]


def test_forbidden_path_request_exits_blocked(tmp_path):
    payload_path = _write_payload(
        tmp_path,
        _payload(
            allowed_paths=[".env"],
            requested_paths=[".env"],
        ),
    )

    result = run_agent_work_submission(payload_path=payload_path, evidence_root=tmp_path / "evidence")

    assert result.exit_code == EXIT_BLOCKED
    assert result.status == "BLOCKED"
    assert "FORBIDDEN_PATH_REQUESTED" in result.payload["scope_decision"]["blockers"]


def test_output_contains_no_order_or_broker_controls(tmp_path):
    payload_path = _write_payload(tmp_path, _payload())

    result = run_agent_work_submission(payload_path=payload_path, evidence_root=tmp_path / "evidence")
    encoded = json.dumps(result.payload, sort_keys=True).lower()

    for forbidden in ["submit_order", "modify_order", "cancel_order", "exit_position", "place_order", "broker_secret"]:
        assert forbidden not in encoded

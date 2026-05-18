from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from agent_system.approval import approve_agent_work
from agent_system.evidence import (
    AgentEvidenceError,
    agent_evidence_schema_contract,
    build_agent_evidence_payload,
    write_agent_evidence,
)
from agent_system.scope_guard import assess_agent_scope
from agent_system.work_contract import normalize_agent_work_request


def _request(**overrides):
    payload = {
        "schema_version": 1,
        "source_agent": "gsd",
        "action": "GENERATE_TESTS",
        "title": "Add evidence tests",
        "scope": "Add behavior tests for safe local agent evidence writes.",
        "allowed_paths": ["tests/"],
        "requested_paths": ["tests/test_agent_evidence.py"],
        "forbidden_paths": ["credentials.py", ".env", "broker_contract/"],
        "requires_human_approval": False,
        "metadata": {"project": "algotradify"},
    }
    payload.update(overrides)
    return normalize_agent_work_request(payload)


def _approved_bundle():
    request = _request()
    scope_decision = assess_agent_scope(request)
    approval_decision = approve_agent_work(scope_decision)
    return request, scope_decision, approval_decision


def test_schema_contract_is_local_audit_only():
    contract = agent_evidence_schema_contract()

    assert contract["contract"] == "agent_evidence_v1"
    assert contract["latest_file"] == "agent_work_latest.json"
    assert contract["daily_file_pattern"] == "agent_work_YYYY-MM-DD.jsonl"
    assert contract["safe_defaults"] == {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
    }
    assert contract["scope"] == "local_audit_evidence_only_no_api_no_ui_no_execution"


def test_build_evidence_payload_contains_request_scope_approval_and_safe_flags():
    request, scope_decision, approval_decision = _approved_bundle()
    payload = build_agent_evidence_payload(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        created_at=datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
    )

    assert payload["schema_version"] == 1
    assert payload["created_at"] == "2026-05-18T12:00:00+00:00"
    assert payload["request"]["title"] == "Add evidence tests"
    assert payload["scope_decision"]["state"] == "APPROVED_FOR_PATCH"
    assert payload["approval_decision"]["state"] == "APPROVED_FOR_PATCH"
    assert payload["safety"] == {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
    }
    assert payload["metadata"] == {
        "contract": "agent_evidence_v1",
        "scope": "local_audit_evidence_only_no_execution",
    }


def test_write_agent_evidence_writes_latest_and_daily_jsonl(tmp_path):
    request, scope_decision, approval_decision = _approved_bundle()

    result = write_agent_evidence(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        root_dir=tmp_path,
        created_at=datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
    )

    latest_path = tmp_path / "agent_work_latest.json"
    daily_path = tmp_path / "agent_work_2026-05-18.jsonl"

    assert result["latest_path"] == str(latest_path)
    assert result["daily_path"] == str(daily_path)
    assert result["read_only"] is True
    assert result["is_order_action"] is False
    assert result["broker_api_called"] is False
    assert result["live_mode_touched"] is False
    assert result["allowed_for_live_execution"] is False

    latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
    daily_lines = daily_path.read_text(encoding="utf-8").splitlines()

    assert latest_payload["approval_decision"]["approved"] is True
    assert len(daily_lines) == 1
    assert json.loads(daily_lines[0])["scope_decision"]["state"] == "APPROVED_FOR_PATCH"


def test_write_agent_evidence_appends_daily_lines(tmp_path):
    request, scope_decision, approval_decision = _approved_bundle()

    for hour in (12, 13):
        write_agent_evidence(
            request=request,
            scope_decision=scope_decision,
            approval_decision=approval_decision,
            root_dir=tmp_path,
            created_at=datetime(2026, 5, 18, hour, 0, tzinfo=timezone.utc),
        )

    daily_path = tmp_path / "agent_work_2026-05-18.jsonl"
    daily_lines = daily_path.read_text(encoding="utf-8").splitlines()

    assert len(daily_lines) == 2
    assert json.loads(daily_lines[0])["created_at"] == "2026-05-18T12:00:00+00:00"
    assert json.loads(daily_lines[1])["created_at"] == "2026-05-18T13:00:00+00:00"


def test_rejected_approval_can_still_be_audited(tmp_path):
    request = _request(action="PLACE_ORDER")
    scope_decision = assess_agent_scope(request)
    approval_decision = approve_agent_work(scope_decision, human_approved=True, approved_by="ram")

    result = write_agent_evidence(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        root_dir=tmp_path,
        created_at=datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
    )

    latest_payload = json.loads((tmp_path / "agent_work_latest.json").read_text(encoding="utf-8"))

    assert result["broker_api_called"] is False
    assert latest_payload["scope_decision"]["state"] == "BLOCKED"
    assert latest_payload["approval_decision"]["approved"] is False
    assert "ORDER_ACTION_FORBIDDEN" in latest_payload["scope_decision"]["blockers"]


def test_payload_builder_rejects_unsafe_safety_block():
    request, scope_decision, approval_decision = _approved_bundle()
    payload = build_agent_evidence_payload(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
    )
    payload["safety"]["broker_api_called"] = True

    from agent_system import evidence as evidence_module

    with pytest.raises(AgentEvidenceError, match="UNSAFE_EVIDENCE_BROKER_API_CALLED"):
        evidence_module._assert_safe_payload(payload)


def test_naive_created_at_is_treated_as_utc():
    request, scope_decision, approval_decision = _approved_bundle()

    payload = build_agent_evidence_payload(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        created_at=datetime(2026, 5, 18, 12, 0),
    )

    assert payload["created_at"] == "2026-05-18T12:00:00+00:00"

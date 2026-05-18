from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json

import pytest

from agent_system.approval import approve_agent_work
from agent_system.evidence import write_agent_evidence
from agent_system.scope_guard import assess_agent_scope
from agent_system.task_store import (
    AgentTaskStoreError,
    agent_task_store_schema_contract,
    build_agent_task_record,
    load_agent_task,
    persist_agent_task,
    query_agent_tasks,
    rebuild_agent_task_index,
)
from agent_system.work_contract import normalize_agent_work_request


def _request(**overrides):
    payload = {
        "schema_version": 1,
        "source_agent": "gsd",
        "action": "GENERATE_TESTS",
        "title": "Add task store tests",
        "scope": "Add deterministic tests for local agent task store.",
        "allowed_paths": ["tests/"],
        "requested_paths": ["tests/test_agent_task_store.py"],
        "forbidden_paths": [".env", "credentials.py", "broker_contract/"],
        "requires_human_approval": False,
        "metadata": {"project": "algotradify"},
    }
    payload.update(overrides)
    return normalize_agent_work_request(payload)


def _bundle(tmp_path, **overrides):
    request = _request(**overrides)
    scope_decision = assess_agent_scope(request)
    approval_decision = approve_agent_work(scope_decision, human_approved=True, approved_by="ram")
    evidence_ref = write_agent_evidence(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        root_dir=tmp_path / "evidence",
        created_at=datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
    )
    record = build_agent_task_record(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        evidence_ref=evidence_ref,
        created_at=datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
    )
    return request, scope_decision, approval_decision, evidence_ref, record


def test_schema_contract_is_local_read_only_store():
    contract = agent_task_store_schema_contract()

    assert contract["contract"] == "agent_task_store_v1"
    assert contract["tasks_dir"] == "runtime/agent_work/tasks"
    assert contract["index_file"] == "runtime/agent_work/agent_task_index.json"
    assert contract["safe_defaults"] == {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
    }
    assert contract["scope"] == "local_task_store_only_no_api_no_ui_no_execution"
    assert "work_id" in contract["query_filters"]


def test_build_agent_task_record_preserves_safe_flags(tmp_path):
    _, _, _, _, record = _bundle(tmp_path)

    assert record.read_only is True
    assert record.is_order_action is False
    assert record.broker_api_called is False
    assert record.live_mode_touched is False
    assert record.allowed_for_live_execution is False
    assert record.metadata == {
        "contract": "agent_task_store_v1",
        "scope": "local_task_record_only_no_api_no_ui_no_execution",
    }


def test_persist_agent_task_writes_task_and_index(tmp_path):
    _, _, _, _, record = _bundle(tmp_path)

    result = persist_agent_task(record, root_dir=tmp_path / "store")

    assert result["status"] == "CREATED"
    assert result["work_id"] == record.work_id
    assert result["index_count"] == 1
    assert result["read_only"] is True
    assert result["broker_api_called"] is False

    task_path = tmp_path / "store" / "tasks" / f"{record.work_id}.json"
    index_path = tmp_path / "store" / "agent_task_index.json"
    assert task_path.exists()
    assert index_path.exists()

    saved = json.loads(task_path.read_text(encoding="utf-8"))
    assert saved["work_id"] == record.work_id
    assert saved["state"] == "APPROVED_FOR_PATCH"


def test_load_missing_task_returns_none(tmp_path):
    assert load_agent_task(tmp_path / "store", "missing") is None


def test_persist_identical_duplicate_is_noop(tmp_path):
    _, _, _, _, record = _bundle(tmp_path)
    root = tmp_path / "store"

    first = persist_agent_task(record, root_dir=root)
    second = persist_agent_task(record, root_dir=root)

    assert first["status"] == "CREATED"
    assert second["status"] == "EXISTS"
    assert second["index_count"] == 1


def test_persist_conflicting_duplicate_blocks(tmp_path):
    _, _, _, _, record = _bundle(tmp_path)
    root = tmp_path / "store"
    persist_agent_task(record, root_dir=root)

    conflicting = replace(record, state="REJECTED")

    with pytest.raises(AgentTaskStoreError, match="TASK_ID_CONFLICT"):
        persist_agent_task(conflicting, root_dir=root)


def test_rebuild_index_fails_closed_on_corrupt_task_file(tmp_path):
    tasks = tmp_path / "store" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "bad.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(AgentTaskStoreError, match="TASK_FILE_CORRUPT:bad.json"):
        rebuild_agent_task_index(tmp_path / "store")


def test_rebuild_index_fails_closed_on_unsafe_task_file(tmp_path):
    _, _, _, _, record = _bundle(tmp_path)
    root = tmp_path / "store"
    persist_agent_task(record, root_dir=root)

    task_path = root / "tasks" / f"{record.work_id}.json"
    payload = json.loads(task_path.read_text(encoding="utf-8"))
    payload["broker_api_called"] = True
    task_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AgentTaskStoreError, match="UNSAFE_TASK_BROKER_API_CALLED"):
        rebuild_agent_task_index(root)


def test_query_agent_tasks_filters_by_source_action_state_and_risk(tmp_path):
    root = tmp_path / "store"
    _, _, _, _, first = _bundle(tmp_path, title="First task")
    _, _, _, _, second = _bundle(
        tmp_path,
        title="Second task",
        action="GENERATE_PATCH",
        allowed_paths=["agent_system/"],
        requested_paths=["agent_system/task_store.py"],
    )
    persist_agent_task(first, root_dir=root)
    persist_agent_task(second, root_dir=root)

    by_action = query_agent_tasks(root, action="GENERATE_TESTS")
    assert by_action["source_count"] == 2
    assert by_action["result_count"] == 1
    assert by_action["records"][0]["work_id"] == first.work_id

    by_state = query_agent_tasks(root, state="WAITING_HUMAN_APPROVAL")
    assert by_state["result_count"] == 1
    assert by_state["records"][0]["work_id"] == second.work_id

    by_risk = query_agent_tasks(root, risk_level="MEDIUM")
    assert by_risk["result_count"] == 1
    assert by_risk["records"][0]["work_id"] == second.work_id


def test_query_agent_tasks_filters_by_work_id_and_date_range(tmp_path):
    root = tmp_path / "store"
    _, _, _, _, first = _bundle(tmp_path, title="First task")
    request = _request(title="Later task")
    scope_decision = assess_agent_scope(request)
    approval_decision = approve_agent_work(scope_decision)
    later = build_agent_task_record(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        evidence_ref=None,
        created_at=datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc),
    )
    persist_agent_task(first, root_dir=root)
    persist_agent_task(later, root_dir=root)

    by_id = query_agent_tasks(root, work_id=later.work_id)
    assert by_id["result_count"] == 1
    assert by_id["records"][0]["work_id"] == later.work_id

    by_date = query_agent_tasks(root, created_from="2026-05-19T00:00:00+00:00")
    assert by_date["result_count"] == 1
    assert by_date["records"][0]["work_id"] == later.work_id

    before = query_agent_tasks(root, created_to="2026-05-18T23:59:59+00:00")
    assert before["result_count"] == 1
    assert before["records"][0]["work_id"] == first.work_id


def test_query_agent_tasks_limit_and_safe_flags(tmp_path):
    root = tmp_path / "store"
    _, _, _, _, first = _bundle(tmp_path, title="First task")
    _, _, _, _, second = _bundle(tmp_path, title="Second task")
    persist_agent_task(first, root_dir=root)
    persist_agent_task(second, root_dir=root)

    result = query_agent_tasks(root, limit=1)

    assert result["result_count"] == 1
    assert result["read_only"] is True
    assert result["is_order_action"] is False
    assert result["broker_api_called"] is False
    assert result["live_mode_touched"] is False
    assert result["allowed_for_live_execution"] is False


def test_query_negative_limit_blocks(tmp_path):
    with pytest.raises(AgentTaskStoreError, match="LIMIT_MUST_BE_NON_NEGATIVE"):
        query_agent_tasks(tmp_path / "store", limit=-1)


def test_task_record_rejects_unsafe_approval_payload(tmp_path):
    request, scope_decision, approval_decision, evidence_ref, _ = _bundle(tmp_path)
    unsafe_approval = replace(approval_decision, allowed_for_broker_api=True)

    with pytest.raises(AgentTaskStoreError, match="UNSAFE_TASK_ALLOWED_FOR_BROKER_API"):
        build_agent_task_record(
            request=request,
            scope_decision=scope_decision,
            approval_decision=unsafe_approval,
            evidence_ref=evidence_ref,
        )

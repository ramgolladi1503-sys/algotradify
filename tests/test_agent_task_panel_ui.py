from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_MAIN = FRONTEND_DIR / "main.jsx"
AGENT_PANEL = FRONTEND_DIR / "agentTaskPanel.jsx"


def _main_source() -> str:
    return FRONTEND_MAIN.read_text(encoding="utf-8")


def _panel_source() -> str:
    return AGENT_PANEL.read_text(encoding="utf-8")


def _combined_source() -> str:
    return _main_source() + "\n" + _panel_source()


def _fixture_payload() -> dict:
    return {
        "contract": "agent_tasks_query_v1",
        "source_count": 2,
        "result_count": 2,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
        "records": [
            {
                "work_id": "agent_work_001",
                "source_agent": "gsd",
                "action": "GENERATE_TESTS",
                "state": "APPROVED_FOR_PATCH",
                "risk_level": "LOW",
                "created_at": "2026-05-18T19:00:00+00:00",
                "read_only": True,
                "is_order_action": False,
                "broker_api_called": False,
                "live_mode_touched": False,
                "allowed_for_live_execution": False,
            },
            {
                "work_id": "agent_work_002",
                "source_agent": "gsd",
                "action": "GENERATE_PATCH",
                "state": "WAITING_HUMAN_APPROVAL",
                "risk_level": "MEDIUM",
                "created_at": "2026-05-18T19:05:00+00:00",
                "read_only": True,
                "is_order_action": False,
                "broker_api_called": False,
                "live_mode_touched": False,
                "allowed_for_live_execution": False,
            },
        ],
    }


def test_agent_task_panel_component_exists_and_is_wired():
    main_source = _main_source()
    panel_source = _panel_source()

    assert "from './agentTaskPanel.jsx'" in main_source
    assert "AgentTaskPanel" in main_source
    assert "export function AgentTaskPanel" in panel_source
    assert "Agent Task Dashboard Read-only Panel" in panel_source


def test_agent_task_panel_fetches_read_only_query_endpoint():
    source = _main_source()

    required_terms = [
        "agentTasks: null",
        "['agentTasks', '/agent/tasks?limit=20']",
        "read-only agent task panel",
        "<AgentTaskPanel agentTasks={state.agentTasks} />",
    ]
    for term in required_terms:
        assert term in source


def test_agent_task_panel_renders_query_contract_sections():
    source = _panel_source()

    required_terms = [
        "Agent task API safety flags",
        "Agent task state distribution",
        "Agent task records",
        "agent task query raw payload",
        "contract",
        "source_count",
        "result_count",
        "work_id",
        "source_agent",
        "action",
        "state",
        "risk_level",
        "created_at",
        "read_only",
        "is_order_action",
        "broker_api_called",
        "live_mode_touched",
        "allowed_for_live_execution",
    ]
    for term in required_terms:
        assert term in source


def test_agent_task_panel_exposes_safe_flags_visibly():
    source = _panel_source()

    required_terms = [
        "READ_ONLY_AGENT_TASK_PANEL",
        "AGENT_TASK_QUERY_UNAVAILABLE",
        "agentTaskSafeFlagWarnings",
        "AgentTaskSafeFlagPanel",
        "top-level read_only is not true",
        "top-level is_order_action is not false",
        "top-level broker_api_called is not false",
        "top-level live_mode_touched is not false",
        "top-level allowed_for_live_execution is not false",
        "Agent task query is read-only with broker, order-action, and live-execution flags disabled.",
    ]
    for term in required_terms:
        assert term in source


def test_agent_task_panel_does_not_add_write_or_execution_controls():
    source = _combined_source()

    forbidden_terms = [
        "Approve Task",
        "Reject Task",
        "Run Task",
        "Execute Task",
        "Merge Task",
        "Auto Merge Task",
        "Submit Agent Order",
        "Place Agent Order",
        "Enable Live",
        "Change Live Config",
        "append=true",
    ]
    for term in forbidden_terms:
        assert term not in source


def test_agent_task_fixture_snapshot_shape_is_read_only():
    payload = _fixture_payload()

    snapshot = {
        "contract": payload["contract"],
        "source_count": payload["source_count"],
        "result_count": payload["result_count"],
        "read_only": payload["read_only"],
        "is_order_action": payload["is_order_action"],
        "broker_api_called": payload["broker_api_called"],
        "live_mode_touched": payload["live_mode_touched"],
        "allowed_for_live_execution": payload["allowed_for_live_execution"],
        "record_ids": [record["work_id"] for record in payload["records"]],
        "states": [record["state"] for record in payload["records"]],
        "risk_levels": [record["risk_level"] for record in payload["records"]],
    }

    assert snapshot == {
        "contract": "agent_tasks_query_v1",
        "source_count": 2,
        "result_count": 2,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
        "record_ids": ["agent_work_001", "agent_work_002"],
        "states": ["APPROVED_FOR_PATCH", "WAITING_HUMAN_APPROVAL"],
        "risk_levels": ["LOW", "MEDIUM"],
    }


def test_agent_task_fixture_never_claims_execution_permissions():
    serialized = json.dumps(_fixture_payload())

    forbidden_fragments = [
        '"is_order_action": true',
        '"broker_api_called": true',
        '"live_mode_touched": true',
        '"allowed_for_live_execution": true',
        "real_order_id",
        "broker_secret",
        "submit_order",
        "modify_order",
        "cancel_order",
        "exit_position",
        "auto_merge",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in serialized

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.agent_tasks import agent_tasks_intake_schema_contract, install_agent_tasks_route


def _client(tmp_path) -> TestClient:
    app = FastAPI()
    install_agent_tasks_route(app, root_dir_provider=lambda: tmp_path / "agent_work")
    return TestClient(app)


def _payload(**overrides):
    payload = {
        "schema_version": 1,
        "source_agent": "gsd",
        "action": "GENERATE_TESTS",
        "title": "Add agent tasks API tests",
        "scope": "Add deterministic API tests for agent task intake only.",
        "allowed_paths": ["tests/"],
        "requested_paths": ["tests/test_agent_tasks_api.py"],
        "forbidden_paths": [".env", "credentials.py", "broker_contract/"],
        "requires_human_approval": False,
        "metadata": {"project": "algotradify"},
    }
    payload.update(overrides)
    return payload


def test_schema_contract_is_intake_only():
    contract = agent_tasks_intake_schema_contract()

    assert contract == {
        "contract": "agent_tasks_intake_v1",
        "route": "POST /agent/tasks",
        "method": "POST",
        "safe_defaults": {
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
        },
        "scope": "intake_only_no_execution_no_broker_no_live_no_paper_orders",
    }


def test_post_agent_tasks_approves_docs_tests_request_and_persists_task(tmp_path):
    response = _client(tmp_path).post("/agent/tasks", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["contract"] == "agent_tasks_intake_v1"
    assert body["status"] == "APPROVED_FOR_PATCH"
    assert body["accepted"] is True
    assert body["scope_decision"]["state"] == "APPROVED_FOR_PATCH"
    assert body["approval_decision"]["approved"] is True
    assert body["task_ref"]["status"] == "CREATED"
    assert body["read_only"] is True
    assert body["is_order_action"] is False
    assert body["broker_api_called"] is False
    assert body["live_mode_touched"] is False
    assert body["allowed_for_live_execution"] is False
    assert (tmp_path / "agent_work" / "tasks" / f"{body['work_id']}.json").exists()


def test_post_agent_tasks_blocks_order_action_but_audits_it(tmp_path):
    response = _client(tmp_path).post("/agent/tasks", json=_payload(action="PLACE_ORDER"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED"
    assert body["accepted"] is False
    assert body["scope_decision"]["state"] == "BLOCKED"
    assert body["approval_decision"]["approved"] is False
    assert "ORDER_ACTION_FORBIDDEN" in body["scope_decision"]["blockers"]
    assert body["is_order_action"] is False
    assert body["broker_api_called"] is False
    assert body["allowed_for_live_execution"] is False
    assert (tmp_path / "agent_work" / "tasks" / f"{body['work_id']}.json").exists()


def test_post_agent_tasks_blocks_broker_api_action(tmp_path):
    response = _client(tmp_path).post("/agent/tasks", json=_payload(action="CALL_BROKER_API"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED"
    assert "BROKER_API_FORBIDDEN" in body["scope_decision"]["blockers"]
    assert body["broker_api_called"] is False


def test_post_agent_tasks_blocks_live_action(tmp_path):
    response = _client(tmp_path).post("/agent/tasks", json=_payload(action="ENABLE_LIVE"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED"
    assert "LIVE_ACTION_FORBIDDEN" in body["scope_decision"]["blockers"]
    assert body["live_mode_touched"] is False
    assert body["allowed_for_live_execution"] is False


def test_post_agent_tasks_human_gated_request_rejected_without_approval(tmp_path):
    response = _client(tmp_path).post(
        "/agent/tasks",
        json=_payload(
            action="GENERATE_PATCH",
            allowed_paths=["agent_system/"],
            requested_paths=["agent_system/approval.py"],
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["accepted"] is False
    assert body["scope_decision"]["state"] == "WAITING_HUMAN_APPROVAL"
    assert "HUMAN_APPROVAL_REQUIRED" in body["approval_decision"]["blockers"]


def test_post_agent_tasks_human_gated_request_can_be_patch_approved(tmp_path):
    response = _client(tmp_path).post(
        "/agent/tasks",
        json=_payload(
            action="GENERATE_PATCH",
            allowed_paths=["agent_system/"],
            requested_paths=["agent_system/approval.py"],
            human_approved=True,
            approved_by="ram",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED_FOR_PATCH"
    assert body["accepted"] is True
    assert body["approval_decision"]["approved_by"] == "ram"
    assert body["approval_decision"]["allowed_for_patch"] is True
    assert body["approval_decision"]["allowed_for_broker_api"] is False
    assert body["approval_decision"]["allowed_for_live_execution"] is False
    assert body["approval_decision"]["allowed_for_runtime_wiring"] is False


def test_post_agent_tasks_rejects_malformed_shape(tmp_path):
    response = _client(tmp_path).post("/agent/tasks", json=[])

    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["status"] == "INPUT_ERROR"
    assert body["message"] == "PAYLOAD_JSON_MUST_BE_OBJECT"
    assert body["read_only"] is True
    assert body["broker_api_called"] is False
    assert body["allowed_for_live_execution"] is False


def test_post_agent_tasks_rejects_unknown_source(tmp_path):
    response = _client(tmp_path).post("/agent/tasks", json=_payload(source_agent="unknown"))

    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["status"] == "INPUT_ERROR"
    assert body["message"] == "SOURCE_AGENT_UNKNOWN"
    assert body["read_only"] is True
    assert body["is_order_action"] is False


def test_post_agent_tasks_rejects_non_string_approved_by(tmp_path):
    response = _client(tmp_path).post("/agent/tasks", json=_payload(human_approved=True, approved_by=123))

    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["status"] == "INPUT_ERROR"
    assert body["message"] == "APPROVED_BY_MUST_BE_STRING"
    assert body["broker_api_called"] is False


def test_install_route_is_idempotent(tmp_path):
    app = FastAPI()
    install_agent_tasks_route(app, root_dir_provider=lambda: tmp_path / "agent_work")
    install_agent_tasks_route(app, root_dir_provider=lambda: tmp_path / "agent_work")

    paths = [getattr(route, "path", None) for route in app.routes]
    assert paths.count("/agent/tasks") == 1


def test_output_contains_no_execution_controls(tmp_path):
    response = _client(tmp_path).post("/agent/tasks", json=_payload())

    encoded = response.text.lower()
    for forbidden in [
        "submit_order",
        "modify_order",
        "cancel_order",
        "exit_position",
        "place_order_now",
        "broker_secret",
        "enable_live_now",
    ]:
        assert forbidden not in encoded

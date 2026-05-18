from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.agent_tasks import (
    agent_tasks_query_schema_contract,
    build_agent_task_query_payload,
    install_agent_tasks_route,
)


def _client(tmp_path) -> TestClient:
    app = FastAPI()
    install_agent_tasks_route(app, root_dir_provider=lambda: tmp_path / "agent_work")
    return TestClient(app)


def _payload(**overrides):
    payload = {
        "schema_version": 1,
        "source_agent": "gsd",
        "action": "GENERATE_TESTS",
        "title": "Add agent task query API tests",
        "scope": "Add deterministic API tests for read-only agent task lookup.",
        "allowed_paths": ["tests/"],
        "requested_paths": ["tests/test_agent_tasks_query_api.py"],
        "forbidden_paths": [".env", "credentials.py", "broker_contract/"],
        "requires_human_approval": False,
        "metadata": {"project": "algotradify"},
    }
    payload.update(overrides)
    return payload


def _submit(client: TestClient, **overrides) -> dict:
    response = client.post("/agent/tasks", json=_payload(**overrides))
    assert response.status_code == 200
    return response.json()


def test_query_schema_contract_is_read_only():
    contract = agent_tasks_query_schema_contract()

    assert contract == {
        "contract": "agent_tasks_query_v1",
        "routes": ["GET /agent/tasks", "GET /agent/tasks/{work_id}"],
        "methods": ["GET"],
        "filters": [
            "source_agent",
            "action",
            "state",
            "risk_level",
            "created_from",
            "created_to",
            "limit",
        ],
        "safe_defaults": {
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
        },
        "scope": "query_only_no_execution_no_approval_no_broker_no_live_no_paper_orders",
    }


def test_get_agent_tasks_lists_read_only_task_summaries(tmp_path):
    client = _client(tmp_path)
    submitted = _submit(client)

    response = client.get("/agent/tasks")

    assert response.status_code == 200
    body = response.json()
    assert body["contract"] == "agent_tasks_query_v1"
    assert body["source_count"] == 1
    assert body["result_count"] == 1
    assert body["records"][0]["work_id"] == submitted["work_id"]
    assert body["read_only"] is True
    assert body["is_order_action"] is False
    assert body["broker_api_called"] is False
    assert body["live_mode_touched"] is False
    assert body["allowed_for_live_execution"] is False


def test_get_agent_tasks_filters_by_source_action_state_and_risk(tmp_path):
    client = _client(tmp_path)
    first = _submit(client, title="First task")
    second = _submit(
        client,
        title="Second task",
        action="GENERATE_PATCH",
        allowed_paths=["agent_system/"],
        requested_paths=["agent_system/approval.py"],
    )

    by_action = client.get("/agent/tasks", params={"action": "GENERATE_TESTS"}).json()
    assert by_action["source_count"] == 2
    assert by_action["result_count"] == 1
    assert by_action["records"][0]["work_id"] == first["work_id"]

    by_state = client.get("/agent/tasks", params={"state": "WAITING_HUMAN_APPROVAL"}).json()
    assert by_state["result_count"] == 1
    assert by_state["records"][0]["work_id"] == second["work_id"]

    by_risk = client.get("/agent/tasks", params={"risk_level": "MEDIUM"}).json()
    assert by_risk["result_count"] == 1
    assert by_risk["records"][0]["work_id"] == second["work_id"]

    by_source = client.get("/agent/tasks", params={"source_agent": "gsd"}).json()
    assert by_source["result_count"] == 2


def test_get_agent_tasks_limit_is_read_only_and_validated(tmp_path):
    client = _client(tmp_path)
    _submit(client, title="First task")
    _submit(client, title="Second task")

    response = client.get("/agent/tasks", params={"limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["source_count"] == 2
    assert body["result_count"] == 1
    assert body["read_only"] is True
    assert body["broker_api_called"] is False

    bad = client.get("/agent/tasks", params={"limit": -1})
    assert bad.status_code == 422


def test_get_agent_task_detail_returns_full_task_read_only(tmp_path):
    client = _client(tmp_path)
    submitted = _submit(client)

    response = client.get(f"/agent/tasks/{submitted['work_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["contract"] == "agent_tasks_query_v1"
    assert body["work_id"] == submitted["work_id"]
    assert body["task"]["work_id"] == submitted["work_id"]
    assert body["task"]["request"]["title"] == "Add agent task query API tests"
    assert body["read_only"] is True
    assert body["is_order_action"] is False
    assert body["broker_api_called"] is False
    assert body["live_mode_touched"] is False
    assert body["allowed_for_live_execution"] is False


def test_get_agent_task_detail_missing_returns_safe_404(tmp_path):
    response = _client(tmp_path).get("/agent/tasks/missing-work-id")

    assert response.status_code == 404
    body = response.json()["detail"]
    assert body["status"] == "NOT_FOUND"
    assert body["message"] == "AGENT_TASK_NOT_FOUND"
    assert body["read_only"] is True
    assert body["broker_api_called"] is False
    assert body["allowed_for_live_execution"] is False


def test_query_error_on_corrupt_task_file_fails_closed(tmp_path):
    client = _client(tmp_path)
    _submit(client)
    tasks_dir = tmp_path / "agent_work" / "tasks"
    bad_path = tasks_dir / "bad.json"
    bad_path.write_text("{not-json", encoding="utf-8")

    response = client.get("/agent/tasks")

    assert response.status_code == 500
    body = response.json()["detail"]
    assert body["status"] == "QUERY_ERROR"
    assert "TASK_FILE_CORRUPT" in body["message"]
    assert body["read_only"] is True
    assert body["is_order_action"] is False
    assert body["broker_api_called"] is False
    assert body["live_mode_touched"] is False
    assert body["allowed_for_live_execution"] is False


def test_install_route_keeps_post_and_get_routes_idempotent(tmp_path):
    app = FastAPI()
    install_agent_tasks_route(app, root_dir_provider=lambda: tmp_path / "agent_work")
    install_agent_tasks_route(app, root_dir_provider=lambda: tmp_path / "agent_work")

    route_keys = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        for method in methods:
            if path and path.startswith("/agent/tasks"):
                route_keys.append((method, path))

    assert route_keys.count(("POST", "/agent/tasks")) == 1
    assert route_keys.count(("GET", "/agent/tasks")) == 1
    assert route_keys.count(("GET", "/agent/tasks/{work_id}")) == 1


def test_query_payload_helper_has_no_execution_flags(tmp_path):
    client = _client(tmp_path)
    _submit(client)

    payload = build_agent_task_query_payload(root_dir=tmp_path / "agent_work")

    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["live_mode_touched"] is False
    assert payload["allowed_for_live_execution"] is False


def test_query_output_contains_no_approval_or_execution_controls(tmp_path):
    client = _client(tmp_path)
    _submit(client)

    encoded = client.get("/agent/tasks").text.lower()

    for forbidden in [
        "approve_task",
        "reject_task",
        "submit_order",
        "modify_order",
        "cancel_order",
        "exit_position",
        "place_order_now",
        "broker_secret",
        "enable_live_now",
        "auto_merge",
    ]:
        assert forbidden not in encoded

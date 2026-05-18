from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.agent_tasks import (
    agent_tasks_patch_approval_api_schema_contract,
    install_agent_tasks_route,
)
from agent_system.patch_approval import load_agent_patch_approval


def _client(tmp_path) -> TestClient:
    app = FastAPI()
    install_agent_tasks_route(app, root_dir_provider=lambda: tmp_path / "agent_work")
    return TestClient(app)


def _payload(**overrides):
    payload = {
        "schema_version": 1,
        "source_agent": "gsd",
        "action": "GENERATE_PATCH",
        "title": "Patch agent approval flow",
        "scope": "Patch a safe agent-system file after human review.",
        "allowed_paths": ["agent_system/"],
        "requested_paths": ["agent_system/approval.py"],
        "forbidden_paths": [".env", "credentials.py", "broker_contract/"],
        "requires_human_approval": True,
        "metadata": {"project": "algotradify"},
    }
    payload.update(overrides)
    return payload


def _create_waiting_task(client: TestClient) -> str:
    response = client.post("/agent/tasks", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["scope_decision"]["state"] == "WAITING_HUMAN_APPROVAL"
    return body["work_id"]


def _create_blocked_task(client: TestClient) -> str:
    response = client.post("/agent/tasks", json=_payload(action="PLACE_ORDER", allowed_paths=["tests/"], requested_paths=["tests/test_agent_tasks_patch_approval_api.py"]))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED"
    return body["work_id"]


def test_patch_approval_api_schema_contract_is_record_only():
    contract = agent_tasks_patch_approval_api_schema_contract()

    assert contract == {
        "contract": "agent_tasks_patch_approval_api_v1",
        "routes": [
            "POST /agent/tasks/{work_id}/approval",
            "POST /agent/tasks/{work_id}/rejection",
        ],
        "methods": ["POST"],
        "record_contract": "agent_patch_approval_v1",
        "safe_defaults": {
            "read_only": True,
            "patch_approval_only": True,
            "allowed_for_patch": False,
            "allowed_for_runtime_wiring": False,
            "allowed_for_broker_api": False,
            "allowed_for_live_execution": False,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "real_order_id": None,
        },
        "scope": "patch_approval_api_record_only_no_execution_no_broker_no_live_no_paper_orders",
    }


def test_patch_approval_endpoint_approves_waiting_task_and_records_decision(tmp_path):
    client = _client(tmp_path)
    work_id = _create_waiting_task(client)

    response = client.post(f"/agent/tasks/{work_id}/approval", json={"approved_by": "ram", "reason": "reviewed patch scope"})

    assert response.status_code == 200
    body = response.json()
    assert body["contract"] == "agent_tasks_patch_approval_api_v1"
    assert body["status"] == "APPROVED_FOR_PATCH"
    assert body["work_id"] == work_id
    assert body["read_only"] is True
    assert body["patch_approval_only"] is True
    assert body["allowed_for_patch"] is True
    assert body["allowed_for_runtime_wiring"] is False
    assert body["allowed_for_broker_api"] is False
    assert body["allowed_for_live_execution"] is False
    assert body["is_order_action"] is False
    assert body["broker_api_called"] is False
    assert body["live_mode_touched"] is False
    assert body["real_order_id"] is None
    record = body["approval_record"]
    assert record["decision"] == "APPROVED_FOR_PATCH"
    assert record["approved_by"] == "ram"
    assert record["reason"] == "reviewed patch scope"
    assert record["approval_decision"]["approved"] is True
    assert record["approval_decision"]["allowed_for_patch"] is True
    assert (tmp_path / "agent_work" / "approvals" / f"{work_id}.json").exists()
    loaded = load_agent_patch_approval(tmp_path / "agent_work", work_id)
    assert loaded["decision"] == "APPROVED_FOR_PATCH"


def test_patch_rejection_endpoint_records_rejection_without_patch_permission(tmp_path):
    client = _client(tmp_path)
    work_id = _create_waiting_task(client)

    response = client.post(f"/agent/tasks/{work_id}/rejection", json={"rejected_by": "ram", "reason": "scope unclear"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED_FOR_PATCH"
    assert body["allowed_for_patch"] is False
    assert body["broker_api_called"] is False
    assert body["allowed_for_live_execution"] is False
    record = body["approval_record"]
    assert record["decision"] == "REJECTED_FOR_PATCH"
    assert record["approved"] is False
    assert record["rejected_by"] == "ram"
    assert record["reason"] == "scope unclear"
    assert record["allowed_for_patch"] is False
    loaded = load_agent_patch_approval(tmp_path / "agent_work", work_id)
    assert loaded["decision"] == "REJECTED_FOR_PATCH"


def test_patch_approval_endpoint_requires_existing_task(tmp_path):
    response = _client(tmp_path).post("/agent/tasks/missing-work/approval", json={"approved_by": "ram"})

    assert response.status_code == 404
    body = response.json()["detail"]
    assert body["status"] == "NOT_FOUND"
    assert body["message"] == "AGENT_TASK_NOT_FOUND"
    assert body["patch_approval_only"] is True
    assert body["broker_api_called"] is False
    assert body["allowed_for_live_execution"] is False


def test_patch_approval_endpoint_rejects_missing_approved_by(tmp_path):
    client = _client(tmp_path)
    work_id = _create_waiting_task(client)

    response = client.post(f"/agent/tasks/{work_id}/approval", json={})

    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["status"] == "INPUT_ERROR"
    assert body["message"] == "APPROVED_BY_MUST_BE_STRING"
    assert body["patch_approval_only"] is True
    assert body["is_order_action"] is False


def test_patch_rejection_endpoint_rejects_missing_rejected_by(tmp_path):
    client = _client(tmp_path)
    work_id = _create_waiting_task(client)

    response = client.post(f"/agent/tasks/{work_id}/rejection", json={})

    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["status"] == "INPUT_ERROR"
    assert body["message"] == "REJECTED_BY_MUST_BE_STRING"
    assert body["broker_api_called"] is False


def test_patch_approval_endpoint_blocks_non_object_payload(tmp_path):
    client = _client(tmp_path)
    work_id = _create_waiting_task(client)

    response = client.post(f"/agent/tasks/{work_id}/approval", json=[])

    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["status"] == "INPUT_ERROR"
    assert body["message"] == "PAYLOAD_JSON_MUST_BE_OBJECT"
    assert body["allowed_for_patch"] is False


def test_patch_approval_endpoint_cannot_approve_blocked_task(tmp_path):
    client = _client(tmp_path)
    work_id = _create_blocked_task(client)

    response = client.post(f"/agent/tasks/{work_id}/approval", json={"approved_by": "ram"})

    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["status"] == "REJECTED"
    assert body["message"] == "APPROVAL_DECISION_NOT_APPROVED"
    assert body["allowed_for_patch"] is False
    assert body["broker_api_called"] is False
    assert body["allowed_for_live_execution"] is False


def test_patch_approval_endpoint_blocks_duplicate_decision(tmp_path):
    client = _client(tmp_path)
    work_id = _create_waiting_task(client)

    first = client.post(f"/agent/tasks/{work_id}/approval", json={"approved_by": "ram"})
    second = client.post(f"/agent/tasks/{work_id}/rejection", json={"rejected_by": "ram", "reason": "changed mind"})

    assert first.status_code == 200
    assert second.status_code == 409
    body = second.json()["detail"]
    assert body["status"] == "CONFLICT"
    assert body["message"] == "APPROVAL_DECISION_ALREADY_RECORDED"
    assert body["patch_approval_only"] is True
    assert body["is_order_action"] is False


def test_agent_task_detail_includes_patch_approval_record(tmp_path):
    client = _client(tmp_path)
    work_id = _create_waiting_task(client)
    client.post(f"/agent/tasks/{work_id}/approval", json={"approved_by": "ram"})

    response = client.get(f"/agent/tasks/{work_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["patch_approval"]["decision"] == "APPROVED_FOR_PATCH"
    assert body["patch_approval"]["approved_by"] == "ram"
    assert body["read_only"] is True
    assert body["is_order_action"] is False


def test_patch_approval_routes_are_idempotently_installed(tmp_path):
    app = FastAPI()
    install_agent_tasks_route(app, root_dir_provider=lambda: tmp_path / "agent_work")
    install_agent_tasks_route(app, root_dir_provider=lambda: tmp_path / "agent_work")

    route_keys = [(getattr(route, "path", None), tuple(sorted(getattr(route, "methods", set()) or set()))) for route in app.routes]
    assert route_keys.count(("/agent/tasks/{work_id}/approval", ("POST",))) == 1
    assert route_keys.count(("/agent/tasks/{work_id}/rejection", ("POST",))) == 1


def test_patch_approval_output_contains_no_execution_controls(tmp_path):
    client = _client(tmp_path)
    work_id = _create_waiting_task(client)

    response = client.post(f"/agent/tasks/{work_id}/approval", json={"approved_by": "ram"})
    encoded = response.text.lower()

    for forbidden in [
        "submit_order",
        "modify_order",
        "cancel_order",
        "exit_position",
        "place_order_now",
        "broker_secret",
        "enable_live_now",
        "auto_merge",
        "apply_patch_now",
    ]:
        assert forbidden not in encoded

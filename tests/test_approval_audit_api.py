from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.server import app


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_approval_audit_api_reads_json_artifact(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "approval_audit_latest.json",
        {
            "events": [
                {
                    "approval_id": "a1",
                    "candidate_id": "c1",
                    "operator_id": "op1",
                    "status": "APPROVED",
                    "reason": "manual risk review",
                    "ts_epoch": 10,
                    "expires_at_epoch": 100,
                    "safety_decision": {"execution_permitted": False, "status": "BLOCKED"},
                }
            ]
        },
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/approval-audit?now_epoch=50")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c1"
    assert payload["current_status"] == "APPROVED"
    assert payload["approval_id"] == "a1"
    assert payload["operator_id"] == "op1"
    assert payload["approved_count"] == 1
    assert payload["blockers"] == []
    assert payload["events"][0]["immutable_audit_event"] is True
    assert payload["events"][0]["is_order_action"] is False
    assert payload["is_order_action"] is False


def test_approval_audit_api_filters_candidate_id(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "approvals_latest.json",
        [
            {"approval_id": "a1", "candidate_id": "c1", "operator_id": "op1", "status": "APPROVED", "reason": "ok", "ts_epoch": 1},
            {"approval_id": "a2", "candidate_id": "c2", "operator_id": "op2", "status": "REJECTED", "reason": "spread widened", "ts_epoch": 2},
        ],
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/approval-audit?candidate_id=c2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c2"
    assert payload["current_status"] == "REJECTED"
    assert payload["rejected_count"] == 1
    assert payload["blockers"] == ["APPROVAL_REJECTED"]


def test_approval_audit_api_reads_jsonl_artifact(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    (runtime_root / "approval_audit.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"approval_id": "a1", "candidate_id": "c1", "operator_id": "op1", "status": "APPROVED", "reason": "first", "ts_epoch": 1}),
                json.dumps({"approval_id": "a2", "candidate_id": "c1", "operator_id": "op2", "status": "REVOKED", "reason": "market changed", "ts_epoch": 2}),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/approval-audit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_status"] == "REVOKED"
    assert payload["approved_count"] == 1
    assert payload["revoked_count"] == 1
    assert payload["latest_reason"] == "market changed"


def test_approval_audit_api_expiry(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "manual_approvals_latest.json",
        [
            {"approval_id": "a1", "candidate_id": "c1", "operator_id": "op1", "status": "APPROVED", "reason": "time boxed", "ts_epoch": 1, "expires_at_epoch": 5}
        ],
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/approval-audit?now_epoch=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_status"] == "EXPIRED"
    assert payload["expired_count"] == 1
    assert payload["blockers"] == ["APPROVAL_EXPIRED"]
    assert payload["events"][0]["status"] == "EXPIRED"


def test_approval_audit_api_empty_state(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/approval-audit?candidate_id=c1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c1"
    assert payload["current_status"] == "UNKNOWN"
    assert payload["blockers"] == ["NO_APPROVAL_AUDIT_EVENTS"]
    assert payload["events"] == []
    assert payload["is_order_action"] is False

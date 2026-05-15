from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.server import app


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_fill_lifecycle_api_reads_json_artifact(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "fill_lifecycle_latest.json",
        {
            "events": [
                {"candidate_id": "c1", "status": "ORDER_SUBMITTED", "ts_epoch": 1},
                {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 2, "filled_quantity": 50, "average_price": 101.25},
            ]
        },
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/fill-lifecycle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c1"
    assert payload["current_status"] == "FILLED"
    assert payload["filled_quantity"] == 50
    assert payload["average_price"] == 101.25
    assert len(payload["events"]) == 2
    assert payload["is_order_submission"] is False


def test_fill_lifecycle_api_filters_candidate_id(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "orders_latest.json",
        [
            {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 1},
            {"candidate_id": "c2", "status": "REJECTED", "ts_epoch": 2},
        ],
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/fill-lifecycle?candidate_id=c2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c2"
    assert payload["current_status"] == "ORDER_REJECTED"
    assert payload["terminal"] is True
    assert len(payload["events"]) == 1


def test_fill_lifecycle_api_reads_jsonl_artifact(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    (runtime_root / "order_lifecycle.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"candidate_id": "c1", "status": "ORDER_SUBMITTED", "ts_epoch": 1}),
                json.dumps({"candidate_id": "c1", "status": "ORDER_ACCEPTED", "ts_epoch": 2}),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/fill-lifecycle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_status"] == "ORDER_ACCEPTED"
    assert len(payload["events"]) == 2


def test_fill_lifecycle_api_empty_state(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/fill-lifecycle?candidate_id=c1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c1"
    assert payload["current_status"] == "UNKNOWN"
    assert payload["blockers"] == ["NO_FILL_LIFECYCLE_EVENTS"]
    assert payload["events"] == []
    assert payload["is_order_submission"] is False

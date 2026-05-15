from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.server import app


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_outcome_replay_api_reads_json_artifact(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "outcome_replay_latest.json",
        {
            "events": [
                {"candidate_id": "c1", "status": "SELECTED", "ts_epoch": 1, "quality_score": 82},
                {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 2, "quality_score": 85},
            ]
        },
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/outcome-replay")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c1"
    assert payload["current_status"] == "FILLED"
    assert payload["selected_count"] == 1
    assert payload["filled_count"] == 1
    assert payload["best_quality_score"] == 85
    assert payload["is_order_action"] is False


def test_outcome_replay_api_filters_candidate_id(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "outcomes_latest.json",
        [
            {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 1},
            {"candidate_id": "c2", "status": "REJECTED", "ts_epoch": 2, "rejection_reason": "RMS blocked"},
        ],
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/outcome-replay?candidate_id=c2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c2"
    assert payload["current_status"] == "REJECTED"
    assert payload["terminal"] is True
    assert payload["rejected_count"] == 1
    assert payload["events"][0]["reason"] == "RMS blocked"


def test_outcome_replay_api_reads_jsonl_artifact(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    (runtime_root / "outcomes.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"candidate_id": "c1", "status": "BLOCKED", "ts_epoch": 1, "reason": "MISSING_MARKET_READINESS"}),
                json.dumps({"candidate_id": "c1", "status": "SELECTED", "ts_epoch": 2, "quality_score": 90}),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/outcome-replay")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_status"] == "SELECTED"
    assert payload["blocked_count"] == 1
    assert payload["selected_count"] == 1
    assert len(payload["events"]) == 2


def test_outcome_replay_api_empty_state(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/outcome-replay?candidate_id=c1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c1"
    assert payload["current_status"] == "UNKNOWN"
    assert payload["blockers"] == ["NO_OUTCOME_EVENTS"]
    assert payload["events"] == []
    assert payload["is_order_action"] is False

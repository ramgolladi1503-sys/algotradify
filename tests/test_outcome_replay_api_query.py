from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.server import app


def _seed_outcome_replay(tmp_path):
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    (runtime_root / "outcome_replay_latest.json").write_text(
        json.dumps(
            {
                "outcome_replay": [
                    {
                        "candidate_id": "c1",
                        "status": "SELECTED",
                        "strategy": "orb_retest",
                        "ts_epoch": 10,
                        "quality_score": 80,
                    },
                    {
                        "candidate_id": "c1",
                        "status": "FILLED",
                        "strategy": "orb_retest",
                        "ts_epoch": 20,
                        "quality_score": 90,
                    },
                    {
                        "candidate_id": "c2",
                        "status": "REJECTED",
                        "strategy": "vwap_pullback",
                        "ts_epoch": 30,
                    },
                    {
                        "candidate_id": "c3",
                        "status": "BLOCKED",
                        "evidence": {"strategy_family": "zero_hero"},
                        "ts_epoch": 40,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return runtime_root


def test_outcome_replay_api_filters_by_status_strategy_and_time(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _seed_outcome_replay(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/outcome-replay?status=filled&strategy=orb_retest&ts_from_epoch=15&ts_to_epoch=25")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_status"] == "FILLED"
    assert payload["filled_count"] == 1
    assert len(payload["events"]) == 1
    assert payload["events"][0]["candidate_id"] == "c1"
    assert payload["query"] == {
        "candidate_id": None,
        "status": "filled",
        "strategy": "orb_retest",
        "ts_from_epoch": 15.0,
        "ts_to_epoch": 25.0,
        "source_count": 4,
        "result_count": 1,
        "read_only": True,
        "is_order_action": False,
    }
    assert payload["is_order_action"] is False


def test_outcome_replay_api_keeps_candidate_id_filter(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _seed_outcome_replay(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/outcome-replay?candidate_id=c2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c2"
    assert payload["current_status"] == "REJECTED"
    assert payload["rejected_count"] == 1
    assert len(payload["events"]) == 1
    assert payload["query"]["candidate_id"] == "c2"
    assert payload["query"]["read_only"] is True


def test_outcome_replay_api_filters_nested_strategy_family(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _seed_outcome_replay(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/outcome-replay?strategy=zero_hero")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c3"
    assert payload["current_status"] == "BLOCKED"
    assert len(payload["events"]) == 1
    assert payload["query"]["result_count"] == 1


def test_outcome_replay_api_returns_empty_state_for_no_query_match(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _seed_outcome_replay(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/outcome-replay?status=filled&strategy=vwap_pullback")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_status"] == "UNKNOWN"
    assert payload["events"] == []
    assert payload["blockers"] == ["NO_OUTCOME_EVENTS"]
    assert payload["query"]["source_count"] == 4
    assert payload["query"]["result_count"] == 0
    assert payload["query"]["is_order_action"] is False

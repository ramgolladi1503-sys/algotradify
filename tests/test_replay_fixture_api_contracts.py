from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from api.server import app
from outcome_replay.query import _candidate_id


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "replay"
FIXTURE_FILES = [
    "empty_replay.json",
    "single_candidate_lifecycle.json",
    "multi_candidate_mixed_status.json",
]


def _load_fixture(filename: str) -> dict:
    return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))


def _seed_runtime_root(tmp_path, fixture: dict) -> Path:
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    (runtime_root / "outcome_replay_latest.json").write_text(
        json.dumps({"outcome_replay": fixture["outcome_replay"]}),
        encoding="utf-8",
    )
    return runtime_root


def _client_for_fixture(tmp_path, monkeypatch, fixture: dict) -> TestClient:
    import api.server as server

    runtime_root = _seed_runtime_root(tmp_path, fixture)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    return TestClient(app)


def _url_for_case(filters: dict) -> str:
    if not filters:
        return "/outcome-replay"
    return f"/outcome-replay?{urlencode(filters)}"


def test_replay_fixture_api_contracts_for_expected_query_cases(tmp_path, monkeypatch):
    for filename in FIXTURE_FILES:
        fixture = _load_fixture(filename)
        client = _client_for_fixture(tmp_path / fixture["fixture_id"], monkeypatch, fixture)
        source_count = fixture["expected"]["source_count"]

        for case in fixture["expected"]["query_cases"]:
            response = client.get(_url_for_case(case["filters"]))

            assert response.status_code == 200, f"{filename}:{case['name']}"
            payload = response.json()
            assert len(payload["events"]) == case["result_count"], f"{filename}:{case['name']}"
            assert [_candidate_id(row) for row in payload["events"]] == case["candidate_ids"], f"{filename}:{case['name']}"
            assert payload["query"]["source_count"] == source_count
            assert payload["query"]["result_count"] == case["result_count"]
            assert payload["query"]["read_only"] is True
            assert payload["query"]["is_order_action"] is False
            assert payload["is_order_action"] is False


def test_replay_fixture_api_empty_fixture_returns_safe_empty_state(tmp_path, monkeypatch):
    fixture = _load_fixture("empty_replay.json")
    client = _client_for_fixture(tmp_path, monkeypatch, fixture)

    response = client.get("/outcome-replay")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_status"] == "UNKNOWN"
    assert payload["events"] == []
    assert payload["blockers"] == ["NO_OUTCOME_EVENTS"]
    assert payload["query"]["source_count"] == 0
    assert payload["query"]["result_count"] == 0
    assert payload["query"]["read_only"] is True
    assert payload["query"]["is_order_action"] is False


def test_replay_fixture_api_single_candidate_lifecycle_summary(tmp_path, monkeypatch):
    fixture = _load_fixture("single_candidate_lifecycle.json")
    client = _client_for_fixture(tmp_path, monkeypatch, fixture)

    response = client.get("/outcome-replay?candidate_id=c1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c1"
    assert payload["selected_count"] == 1
    assert payload["submitted_count"] == 1
    assert payload["accepted_count"] == 1
    assert payload["filled_count"] == 1
    assert payload["closed_count"] == 1
    assert payload["current_status"] == "CLOSED"
    assert payload["best_quality_score"] == 90
    assert payload["query"]["source_count"] == 5
    assert payload["query"]["result_count"] == 5


def test_replay_fixture_api_mixed_status_summary_and_nested_strategy(tmp_path, monkeypatch):
    fixture = _load_fixture("multi_candidate_mixed_status.json")
    client = _client_for_fixture(tmp_path, monkeypatch, fixture)

    response = client.get("/outcome-replay?strategy=zero_hero")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "c3"
    assert payload["current_status"] == "BLOCKED"
    assert payload["blocked_count"] == 1
    assert payload["query"]["source_count"] == 5
    assert payload["query"]["result_count"] == 1
    assert payload["query"]["strategy"] == "zero_hero"


def test_replay_fixture_api_no_match_preserves_query_metadata(tmp_path, monkeypatch):
    fixture = _load_fixture("multi_candidate_mixed_status.json")
    client = _client_for_fixture(tmp_path, monkeypatch, fixture)

    response = client.get("/outcome-replay?status=filled&strategy=zero_hero")

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"] == []
    assert payload["blockers"] == ["NO_OUTCOME_EVENTS"]
    assert payload["query"]["status"] == "filled"
    assert payload["query"]["strategy"] == "zero_hero"
    assert payload["query"]["source_count"] == 5
    assert payload["query"]["result_count"] == 0
    assert payload["query"]["read_only"] is True
    assert payload["query"]["is_order_action"] is False

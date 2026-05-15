from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dry_run_execution_route import install_dry_run_execution_route


def _top(candidate_id="c1"):
    return {
        "status": "SELECTED",
        "selected": {
            "candidate_id": candidate_id,
            "symbol": "NIFTY26MAY25500CE",
            "tradingsymbol": "NIFTY26MAY25500CE",
            "quality_score": 91,
            "is_order": False,
        },
        "is_order_action": False,
    }


def _readiness(candidate_id="c1"):
    return [{"candidate_id": candidate_id, "execution_allowed": True}]


def _safety(permitted=True):
    return {
        "execution_permitted": permitted,
        "status": "PERMITTED" if permitted else "BLOCKED",
        "is_order_action": False,
        "safety_visibility_only": True,
        "blockers": [] if permitted else ["TEST_BLOCKER"],
    }


def _approval(candidate_id="c1", status="APPROVED"):
    return {
        "candidate_id": candidate_id,
        "current_status": status,
        "approval_id": "approval-1234",
        "operator_id": "op1",
        "events": [
            {
                "approval_id": "approval-1234",
                "candidate_id": candidate_id,
                "operator_id": "op1",
                "status": status,
                "safety_decision": {"execution_permitted": True, "status": "PERMITTED", "is_order_action": False},
                "is_order_action": False,
            }
        ],
        "blockers": [],
        "is_order_action": False,
    }


def _matcher(top, readiness):
    selected = top.get("selected") if isinstance(top, dict) else None
    candidate_id = selected.get("candidate_id") if isinstance(selected, dict) else None
    for row in readiness:
        if row.get("candidate_id") == candidate_id:
            return row
    return None


def _client(tmp_path: Path, *, top=None, safety=None, approval=None):
    app = FastAPI()
    install_dry_run_execution_route(
        app,
        runtime_root_provider=lambda: tmp_path,
        top_executable_provider=lambda limit, min_quality_score: top if top is not None else _top(),
        readiness_provider=lambda limit: _readiness(),
        safety_provider=lambda request, limit, min_quality_score: safety if safety is not None else _safety(),
        approval_provider=lambda candidate_id, now_epoch: approval if approval is not None else _approval(candidate_id or "c1"),
        readiness_matcher=_matcher,
    )
    return TestClient(app)


def test_dry_run_execution_route_blocks_default_missing_evidence(tmp_path):
    client = _client(tmp_path, top={"status": "NONE"}, safety=_safety(False), approval={})

    response = client.get("/dry-run-execution")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is False
    assert payload["dry_run_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert "NO_TOP_EXECUTABLE_SELECTED" in payload["blockers"]
    assert "EXECUTION_SAFETY_NOT_PERMITTED" in payload["blockers"]
    assert "APPROVAL_EVIDENCE_REQUIRED" in payload["blockers"]


def test_dry_run_execution_route_creates_when_evidence_valid(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution?now_epoch=100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    assert payload["candidate_id"] == "c1"
    assert payload["intent"]["dry_run_only"] is True
    assert payload["intent"]["is_order_action"] is False
    assert payload["intent"]["broker_api_called"] is False
    assert payload["intent"]["real_order_id"] is None
    assert payload["lifecycle_event"]["status"] == "DRY_RUN_INTENT_CREATED"
    assert payload["outcome_event"]["evidence"]["dry_run_only"] is True


def test_dry_run_execution_route_append_false_writes_no_files(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution?now_epoch=100&append=false")

    assert response.status_code == 200
    assert response.json()["created"] is True
    assert not (tmp_path / "logs" / "dry_run_order_intents.jsonl").exists()
    assert not (tmp_path / "logs" / "dry_run_lifecycle.jsonl").exists()
    assert not (tmp_path / "logs" / "outcome_replay.jsonl").exists()


def test_dry_run_execution_route_append_true_writes_jsonl(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution?now_epoch=100&append=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    assert set(payload["append_paths"]) == {"intent", "lifecycle", "outcome"}
    intent_rows = [json.loads(line) for line in (tmp_path / "logs" / "dry_run_order_intents.jsonl").read_text(encoding="utf-8").splitlines()]
    lifecycle_rows = [json.loads(line) for line in (tmp_path / "logs" / "dry_run_lifecycle.jsonl").read_text(encoding="utf-8").splitlines()]
    outcome_rows = [json.loads(line) for line in (tmp_path / "logs" / "outcome_replay.jsonl").read_text(encoding="utf-8").splitlines()]
    assert intent_rows[0]["dry_run_only"] is True
    assert lifecycle_rows[0]["broker_api_called"] is False
    assert outcome_rows[0]["real_order_id"] is None


def test_dry_run_execution_route_always_exposes_safe_flags(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False

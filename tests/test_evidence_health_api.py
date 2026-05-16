from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dry_run_execution_route import build_evidence_health_payload, install_dry_run_execution_route


def _top(candidate_id="c1"):
    return {
        "status": "SELECTED",
        "selected": {
            "candidate_id": candidate_id,
            "symbol": "NIFTY26MAY25500CE",
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
        "warnings": [],
    }


def _approval(candidate_id="c1"):
    return {
        "candidate_id": candidate_id,
        "current_status": "APPROVED",
        "approval_id": "approval-1234",
        "operator_id": "op1",
        "events": [],
        "blockers": [],
        "is_order_action": False,
    }


def _matcher(top: dict[str, Any], readiness: list[dict[str, Any]]):
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


def test_evidence_health_endpoint_returns_read_only_integrity_summary(tmp_path):
    client = _client(tmp_path)

    response = client.get("/evidence-health?limit=20&now_epoch=100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_health_only"] is True
    assert payload["dry_run_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["schema_count"] == 7
    assert "dry_run_export_bundle" in payload["results"]
    assert "dry_run_execution_payload" in payload["results"]
    assert payload["results"]["dry_run_export_bundle"]["valid"] is True
    assert not (tmp_path / "logs" / "dry_run_order_intents.jsonl").exists()
    assert not (tmp_path / "logs" / "dry_run_lifecycle.jsonl").exists()
    assert not (tmp_path / "logs" / "outcome_replay.jsonl").exists()


def test_evidence_health_endpoint_degrades_when_evidence_missing(tmp_path):
    client = _client(tmp_path, top={"status": "NONE"}, safety=_safety(False), approval={})

    response = client.get("/evidence-health?limit=20")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "DEGRADED"
    assert payload["invalid_count"] > 0
    assert payload["missing_key_count"] > 0
    assert payload["safe_flag_violation_count"] == 0
    assert payload["results"]["approval_evidence"]["valid"] is False


def test_build_evidence_health_payload_reports_safe_flag_violations():
    payload = build_evidence_health_payload(
        {
            "readiness_snapshot": {"candidate_id": "c1", "execution_allowed": True},
            "lifecycle_event": {
                "status": "BAD",
                "dry_run_only": True,
                "broker_api_called": True,
                "real_order_id": "REAL-1",
            },
        }
    )

    assert payload["status"] == "DEGRADED"
    assert payload["schema_count"] == 2
    assert payload["safe_flag_violation_count"] == 2
    assert payload["results"]["lifecycle_event"]["valid"] is False
    assert {row["key"] for row in payload["results"]["lifecycle_event"]["safe_flag_violations"]} == {
        "broker_api_called",
        "real_order_id",
    }

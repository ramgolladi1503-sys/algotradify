from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.server import app


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _runtime_opportunity(candidate_id: str = "c1"):
    return {
        "candidate_id": candidate_id,
        "symbol": "NIFTY26MAY25500CE",
        "strategy": "orb_retest",
        "strategy_family": "ORB_RETEST",
        "confidence": 90,
    }


def test_execution_readiness_api_uses_runtime_evidence_to_allow_candidate(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "top_opportunities_latest.json",
        {"top_executable_opportunities": [_runtime_opportunity()]},
    )
    _write_json(
        runtime_root / "broker_contract_readiness_latest.json",
        {
            "broker_contract_readiness": [
                {
                    "candidate_id": "c1",
                    "symbol": "NIFTY26MAY25500CE",
                    "readiness_status": "RESOLVED_EXACT",
                    "resolved": True,
                    "instrument_token": 12345,
                    "fallback_used": False,
                    "blockers": [],
                    "warnings": [],
                }
            ]
        },
    )
    _write_json(
        runtime_root / "market_readiness_latest.json",
        {
            "market_readiness": [
                {
                    "candidate_id": "c1",
                    "symbol": "NIFTY26MAY25500CE",
                    "status": "READY",
                    "blockers": [],
                    "warnings": [],
                }
            ]
        },
    )
    _write_json(
        runtime_root / "risk_readiness_latest.json",
        {
            "risk_readiness": [
                {
                    "candidate_id": "c1",
                    "allowed": True,
                    "status": "RISK_OK",
                    "blockers": [],
                    "warnings": [],
                }
            ]
        },
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/execution-readiness")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    record = payload[0]
    assert record["candidate_id"] == "c1"
    assert record["execution_allowed"] is True
    assert record["status"] == "ALLOWED"
    assert record["blockers"] == []
    assert record["is_order"] is False
    assert record["evidence"]["broker_contract"]["instrument_token"] == 12345
    assert record["evidence"]["market_readiness"]["status"] == "READY"
    assert record["evidence"]["risk"]["status"] == "RISK_OK"
    assert record["evidence"]["runtime_evidence_counts"] == {
        "broker_records": 1,
        "market_records": 1,
        "risk_records": 1,
    }


def test_execution_readiness_api_keeps_candidate_blocked_when_market_evidence_missing(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(runtime_root / "top_opportunities_latest.json", {"top_executable_opportunities": [_runtime_opportunity()]})
    _write_json(
        runtime_root / "broker_contract_readiness_latest.json",
        [{"candidate_id": "c1", "readiness_status": "RESOLVED_EXACT", "resolved": True, "blockers": [], "warnings": []}],
    )
    _write_json(
        runtime_root / "risk_readiness_latest.json",
        [{"candidate_id": "c1", "allowed": True, "status": "RISK_OK", "blockers": [], "warnings": []}],
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/execution-readiness")

    assert response.status_code == 200
    record = response.json()[0]
    assert record["execution_allowed"] is False
    assert record["status"] == "BLOCKED_INCOMPLETE_EVIDENCE"
    assert "MISSING_MARKET_READINESS" in record["blockers"]


def test_execution_readiness_api_uses_global_risk_record_when_candidate_specific_absent(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(runtime_root / "top_opportunities_latest.json", {"top_executable_opportunities": [_runtime_opportunity()]})
    _write_json(
        runtime_root / "broker_contract_readiness_latest.json",
        [{"candidate_id": "c1", "readiness_status": "RESOLVED_EXACT", "resolved": True, "blockers": [], "warnings": []}],
    )
    _write_json(
        runtime_root / "market_readiness_latest.json",
        [{"candidate_id": "c1", "status": "READY", "blockers": [], "warnings": []}],
    )
    _write_json(
        runtime_root / "risk_readiness_latest.json",
        {"allowed": False, "status": "DAILY_LOSS_LIMIT", "blockers": ["DAILY_LOSS_LIMIT_HIT"], "warnings": []},
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/execution-readiness")

    assert response.status_code == 200
    record = response.json()[0]
    assert record["execution_allowed"] is False
    assert record["status"] == "BLOCKED_RISK"
    assert "RISK_NOT_ALLOWED:DAILY_LOSS_LIMIT" in record["blockers"]
    assert "RISK:DAILY_LOSS_LIMIT_HIT" in record["blockers"]


def test_execution_readiness_api_can_match_market_by_broker_instrument_token(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(runtime_root / "top_opportunities_latest.json", {"top_executable_opportunities": [_runtime_opportunity()]})
    _write_json(
        runtime_root / "broker_contract_readiness_latest.json",
        [
            {
                "candidate_id": "c1",
                "readiness_status": "RESOLVED_EXACT",
                "resolved": True,
                "instrument_token": 12345,
                "blockers": [],
                "warnings": [],
            }
        ],
    )
    _write_json(
        runtime_root / "market_readiness_latest.json",
        [{"instrument_token": 12345, "status": "READY", "blockers": [], "warnings": []}],
    )
    _write_json(
        runtime_root / "risk_readiness_latest.json",
        [{"candidate_id": "c1", "allowed": True, "status": "RISK_OK", "blockers": [], "warnings": []}],
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/execution-readiness")

    assert response.status_code == 200
    record = response.json()[0]
    assert record["execution_allowed"] is True
    assert record["evidence"]["market_readiness"]["instrument_token"] == 12345

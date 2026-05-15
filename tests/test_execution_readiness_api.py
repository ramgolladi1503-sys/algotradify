from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import app


def test_strategy_execution_readiness_api_blocks_incomplete_evidence():
    client = TestClient(app)

    response = client.get(
        "/strategies/draft-candidates/execution-readiness"
        "?symbol=nifty&orb_retest_score=85"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    record = payload[0]
    assert record["candidate_id"] == "orb_retest:NIFTY:na"
    assert record["execution_allowed"] is False
    assert record["status"] == "BLOCKED_INCOMPLETE_EVIDENCE"
    assert "MISSING_BROKER_CONTRACT_READINESS" in record["blockers"]
    assert "MISSING_MARKET_READINESS" in record["blockers"]
    assert "MISSING_RISK_READINESS" in record["blockers"]
    assert record["is_order"] is False
    assert record["is_execution_readiness_record"] is True


def test_strategy_execution_readiness_api_returns_empty_when_no_drafts():
    client = TestClient(app)

    response = client.get("/strategies/draft-candidates/execution-readiness?symbol=nifty")

    assert response.status_code == 200
    assert response.json() == []


def test_runtime_execution_readiness_api_returns_empty_when_no_opportunities_exist(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/execution-readiness")

    assert response.status_code == 200
    assert response.json() == []


def test_runtime_execution_readiness_api_blocks_missing_downstream_evidence(tmp_path, monkeypatch):
    import json
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    (runtime_root / "top_opportunities_latest.json").write_text(
        json.dumps(
            {
                "top_executable_opportunities": [
                    {
                        "candidate_id": "c1",
                        "symbol": "NIFTY",
                        "strategy": "orb_retest",
                        "strategy_family": "ORB_RETEST",
                        "confidence": 90,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/execution-readiness")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    record = payload[0]
    assert record["candidate_id"] == "c1"
    assert record["execution_allowed"] is False
    assert record["status"] == "BLOCKED_INCOMPLETE_EVIDENCE"
    assert "MISSING_BROKER_CONTRACT_READINESS" in record["blockers"]
    assert "MISSING_MARKET_READINESS" in record["blockers"]
    assert "MISSING_RISK_READINESS" in record["blockers"]
    assert record["evidence"]["candidate_truth"]["truth_status"] == "REAL"
    assert record["evidence"]["opportunity"]["opportunity_status"] == "SELECTED"

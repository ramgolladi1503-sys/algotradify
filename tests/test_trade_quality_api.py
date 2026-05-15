from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.server import app


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _opportunity(candidate_id: str, confidence: int, symbol: str):
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "strategy": "orb_retest",
        "strategy_family": "ORB_RETEST",
        "confidence": confidence,
    }


def _broker(candidate_id: str, symbol: str, fallback: bool = False):
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "readiness_status": "RESOLVED_FALLBACK" if fallback else "RESOLVED_EXACT",
        "resolved": True,
        "fallback_used": fallback,
        "blockers": [],
        "warnings": ["FALLBACK_CONTRACT_USED"] if fallback else [],
    }


def _market(candidate_id: str, symbol: str, spread_pct: float):
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "status": "READY",
        "quote": {
            "quote_age_sec": 0.2,
            "max_quote_age_sec": 2.0,
            "spread_pct": spread_pct,
            "max_spread_pct": 1.0,
        },
        "blockers": [],
        "warnings": [],
    }


def _risk(candidate_id: str):
    return {"candidate_id": candidate_id, "allowed": True, "status": "RISK_OK", "blockers": [], "warnings": []}


def test_trade_quality_api_ranks_allowed_candidates(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "top_opportunities_latest.json",
        {
            "top_executable_opportunities": [
                _opportunity("best", 95, "NIFTY26MAY25500CE"),
                _opportunity("weaker", 70, "NIFTY26MAY25600CE"),
            ]
        },
    )
    _write_json(
        runtime_root / "broker_contract_readiness_latest.json",
        [_broker("best", "NIFTY26MAY25500CE"), _broker("weaker", "NIFTY26MAY25600CE", fallback=True)],
    )
    _write_json(
        runtime_root / "market_readiness_latest.json",
        [_market("best", "NIFTY26MAY25500CE", 0.1), _market("weaker", "NIFTY26MAY25600CE", 0.8)],
    )
    _write_json(runtime_root / "risk_readiness_latest.json", [_risk("best"), _risk("weaker")])
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/trade-quality")

    assert response.status_code == 200
    payload = response.json()
    assert [row["candidate_id"] for row in payload] == ["best", "weaker"]
    assert [row["rank"] for row in payload] == [1, 2]
    assert payload[0]["quality_score"] > payload[1]["quality_score"]
    assert payload[0]["is_order"] is False
    assert payload[1]["penalties"]["broker_fallback"] == 5.0


def test_trade_quality_api_scores_blocked_candidate_zero(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(runtime_root / "top_opportunities_latest.json", {"top_executable_opportunities": [_opportunity("blocked", 90, "NIFTY26MAY25500CE")]})
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/trade-quality")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    row = payload[0]
    assert row["candidate_id"] == "blocked"
    assert row["quality_score"] == 0.0
    assert row["status"] == "BLOCKED_NOT_EXECUTION_READY"
    assert "MISSING_BROKER_CONTRACT_READINESS" in row["blockers"]
    assert row["is_order"] is False


def test_trade_quality_api_returns_empty_when_no_opportunities(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/trade-quality")

    assert response.status_code == 200
    assert response.json() == []

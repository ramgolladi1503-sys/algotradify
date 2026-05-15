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


def _broker(candidate_id: str, symbol: str):
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "readiness_status": "RESOLVED_EXACT",
        "resolved": True,
        "fallback_used": False,
        "blockers": [],
        "warnings": [],
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


def _setup_runtime(runtime_root):
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
        [_broker("best", "NIFTY26MAY25500CE"), _broker("weaker", "NIFTY26MAY25600CE")],
    )
    _write_json(
        runtime_root / "market_readiness_latest.json",
        [_market("best", "NIFTY26MAY25500CE", 0.1), _market("weaker", "NIFTY26MAY25600CE", 0.8)],
    )
    _write_json(runtime_root / "risk_readiness_latest.json", [_risk("best"), _risk("weaker")])


def test_top_executable_api_selects_best_quality_candidate(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _setup_runtime(runtime_root)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/top-executable")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SELECTED"
    assert payload["selected"]["candidate_id"] == "best"
    assert payload["selected"]["selected_by"] == "top_executable_selector"
    assert payload["selected"]["is_order"] is False
    assert payload["is_order"] is False
    assert payload["is_selector_decision"] is True
    assert [row["candidate_id"] for row in payload["eligible"]] == ["best", "weaker"]
    assert payload["rejected"] == []


def test_top_executable_api_respects_min_quality_score_threshold(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _setup_runtime(runtime_root)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/top-executable?min_quality_score=99")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NO_ELIGIBLE_CANDIDATES"
    assert payload["selected"] is None
    assert payload["eligible"] == []
    assert len(payload["rejected"]) == 2
    assert all("QUALITY_SCORE_BELOW_THRESHOLD" in row["selector_rejection_reasons"] for row in payload["rejected"])
    assert payload["is_order"] is False


def test_top_executable_api_rejects_blocked_quality_candidate(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(runtime_root / "top_opportunities_latest.json", {"top_executable_opportunities": [_opportunity("blocked", 90, "NIFTY26MAY25500CE")]})
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/top-executable")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NO_ELIGIBLE_CANDIDATES"
    assert payload["selected"] is None
    assert payload["eligible"] == []
    assert payload["rejected"][0]["candidate_id"] == "blocked"
    assert "EXECUTION_NOT_ALLOWED" in payload["rejected"][0]["selector_rejection_reasons"]
    assert payload["is_order"] is False


def test_top_executable_api_empty_state(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/top-executable")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NO_ELIGIBLE_CANDIDATES"
    assert payload["selected"] is None
    assert payload["eligible"] == []
    assert payload["rejected"] == []
    assert payload["reason"] == "no_execution_allowed_quality_candidate"

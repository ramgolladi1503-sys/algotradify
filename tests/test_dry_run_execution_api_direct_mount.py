from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.server import app


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_runtime(tmp_path):
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_json(
        runtime_root / "top_opportunities_latest.json",
        {
            "top_executable_opportunities": [
                {
                    "candidate_id": "c1",
                    "symbol": "NIFTY26MAY25500CE",
                    "strategy": "orb_retest",
                    "strategy_family": "ORB_RETEST",
                    "score": 95,
                    "confidence": 95,
                    "permission": "EXECUTE",
                    "final_action": "EXECUTE",
                }
            ]
        },
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
    _write_json(
        runtime_root / "approval_audit_latest.json",
        {
            "approval_audit": [
                {
                    "approval_id": "approval-1234",
                    "candidate_id": "c1",
                    "operator_id": "op1",
                    "status": "APPROVED",
                    "reason": "manual dry run review",
                    "ts_epoch": 100,
                    "expires_at_epoch": 200,
                    "safety_decision": {
                        "execution_permitted": True,
                        "status": "PERMITTED",
                        "is_order_action": False,
                        "safety_visibility_only": True,
                    },
                    "is_order_action": False,
                }
            ]
        },
    )
    return runtime_root


def test_movement_opportunity_exists_on_direct_main_app():
    client = TestClient(app)

    response = client.get(
        "/movement-opportunity",
        params={
            "symbol": "NIFTY",
            "ts_epoch": 77777.0,
            "spot_ltp": 101.4,
            "vwap": 101.0,
            "orb_high": 101.0,
            "orb_low": 99.5,
            "day_high": 101.2,
            "day_low": 99.0,
            "prev_day_high": 102.0,
            "prev_day_low": 98.0,
            "atr": 1.1,
            "atr_short": 0.7,
            "atr_long": 1.0,
            "range_width_pct": 0.35,
            "volume_z": 1.9,
            "volatility_state": "COMPRESSION",
            "regime_hint": "COMPRESSION",
            "option_ce_ltp": 125.0,
            "option_pe_ltp": 85.0,
            "ce_premium_change": 22.0,
            "pe_premium_change": -4.0,
            "ce_spread_pct": 0.8,
            "pe_spread_pct": 1.1,
            "ce_depth": 650.0,
            "pe_depth": 500.0,
            "option_ltp_age_sec": 1.0,
            "quote_source": "PRIMARY",
            "time_of_day": "OPEN",
            "minutes_since_open": 14,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "/movement-opportunity"
    assert payload["method"] == "GET"
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["context"]["symbol"] == "NIFTY"
    assert payload["context"]["is_order_action"] is False
    assert payload["summary"]["read_only"] is True
    assert payload["summary"]["is_order_action"] is False
    assert payload["pipeline"]["read_only"] is True
    assert payload["pipeline"]["is_order_action"] is False


def test_movement_opportunity_schema_exists_on_direct_main_app():
    client = TestClient(app)

    response = client.get("/movement-opportunity/schema")

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "/movement-opportunity"
    assert payload["method"] == "GET"
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert "ranked_candidates" in payload["response_top_level_keys"]
    assert "pipeline" in payload["response_top_level_keys"]


def test_dry_run_execution_exists_on_direct_app(tmp_path, monkeypatch):
    import api.server as server

    monkeypatch.setattr(server, "_runtime_root", lambda: tmp_path / ".runtime")
    client = TestClient(app)

    response = client.get("/dry-run-execution")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False


def test_dry_run_execution_direct_app_blocks_by_default(tmp_path, monkeypatch):
    import api.server as server

    monkeypatch.setattr(server, "_runtime_root", lambda: tmp_path / ".runtime")
    client = TestClient(app)

    response = client.get("/dry-run-execution")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is False
    assert "NO_TOP_EXECUTABLE_SELECTED" in payload["blockers"]
    assert payload["dry_run_only"] is True
    assert payload["is_order_action"] is False


def test_dry_run_execution_direct_app_creates_with_seeded_runtime(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _seed_runtime(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/dry-run-execution?now_epoch=150&dry_run_required=false&approval_id=approval-1234&operator_id=op1&broker_confirmation_id=b1&warnings_acknowledged=true"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    assert payload["candidate_id"] == "c1"
    assert payload["intent"]["dry_run_only"] is True
    assert payload["intent"]["is_order_action"] is False
    assert payload["intent"]["broker_api_called"] is False
    assert payload["intent"]["real_order_id"] is None


def test_dry_run_execution_direct_app_append_false_writes_nothing(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _seed_runtime(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/dry-run-execution?now_epoch=150&append=false&dry_run_required=false&approval_id=approval-1234&operator_id=op1&broker_confirmation_id=b1&warnings_acknowledged=true"
    )

    assert response.status_code == 200
    assert response.json()["created"] is True
    assert not (runtime_root / "logs" / "dry_run_order_intents.jsonl").exists()
    assert not (runtime_root / "logs" / "dry_run_lifecycle.jsonl").exists()
    assert not (runtime_root / "logs" / "outcome_replay.jsonl").exists()


def test_dry_run_execution_direct_app_append_true_writes_jsonl(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _seed_runtime(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/dry-run-execution?now_epoch=150&append=true&dry_run_required=false&approval_id=approval-1234&operator_id=op1&broker_confirmation_id=b1&warnings_acknowledged=true"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    assert (runtime_root / "logs" / "dry_run_order_intents.jsonl").exists()
    assert (runtime_root / "logs" / "dry_run_lifecycle.jsonl").exists()
    assert (runtime_root / "logs" / "outcome_replay.jsonl").exists()


def test_dry_run_execution_export_exists_on_direct_app_and_writes_nothing(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _seed_runtime(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/dry-run-execution/export?now_epoch=150&dry_run_required=false&approval_id=approval-1234&operator_id=op1&broker_confirmation_id=b1&warnings_acknowledged=true"
    )

    assert response.status_code == 200
    bundle = response.json()
    assert bundle["bundle_type"] == "DRY_RUN_EVIDENCE_BUNDLE"
    assert bundle["status"] == "BUNDLE_READY"
    assert bundle["candidate_id"] == "c1"
    assert bundle["dry_run_only"] is True
    assert bundle["is_order_action"] is False
    assert bundle["broker_api_called"] is False
    assert bundle["real_order_id"] is None
    assert bundle["export_preview_only"] is True
    assert not (runtime_root / "logs" / "dry_run_order_intents.jsonl").exists()
    assert not (runtime_root / "logs" / "dry_run_lifecycle.jsonl").exists()
    assert not (runtime_root / "logs" / "outcome_replay.jsonl").exists()


def test_evidence_health_exists_on_direct_app_and_writes_nothing(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _seed_runtime(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/evidence-health?limit=20&now_epoch=150&dry_run_required=false&approval_id=approval-1234&operator_id=op1&broker_confirmation_id=b1&warnings_acknowledged=true"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_health_only"] is True
    assert payload["dry_run_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert "dry_run_export_bundle" in payload["results"]
    assert not (runtime_root / "logs" / "dry_run_order_intents.jsonl").exists()
    assert not (runtime_root / "logs" / "dry_run_lifecycle.jsonl").exists()
    assert not (runtime_root / "logs" / "outcome_replay.jsonl").exists()


def test_direct_app_routes_are_not_registered_twice():
    route_paths = [getattr(route, "path", None) for route in app.routes]

    assert route_paths.count("/movement-opportunity") == 1
    assert route_paths.count("/movement-opportunity/schema") == 1
    assert route_paths.count("/dry-run-execution") == 1
    assert route_paths.count("/dry-run-execution/export") == 1
    assert route_paths.count("/evidence-health") == 1

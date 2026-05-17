from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.server import app


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _allowed_artifacts(tmp_path):
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
                    "score": 90,
                    "confidence": 90,
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
    return runtime_root


def test_execution_safety_api_blocks_by_default_and_defaults_to_sim(tmp_path, monkeypatch):
    import api.server as server

    monkeypatch.setattr(server, "_runtime_root", lambda: tmp_path / ".runtime")
    client = TestClient(app)

    response = client.get("/execution-safety")

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_permitted"] is False
    assert payload["status"] == "BLOCKED"
    assert payload["mode"] == "SIM"
    assert payload["execution_mode_api_parse"]["mode"] == "SIM"
    assert payload["execution_mode_api_parse"]["raw_mode"] is None
    assert payload["execution_mode_api_parse"]["invalid_mode"] is False
    assert "EXECUTION_MODE_DEFAULTED_TO_SIM" in payload["warnings"]
    assert "DRY_RUN_REQUIRED" in payload["blockers"]
    assert "MANUAL_APPROVAL_REQUIRED" in payload["blockers"]
    assert "BROKER_CONFIRMATION_REQUIRED" in payload["blockers"]
    assert payload["is_order_action"] is False
    assert payload["safety_visibility_only"] is True


def test_execution_safety_api_can_show_permitted_paper_preview_only_when_mode_is_explicit(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _allowed_artifacts(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/execution-safety?mode=PAPER&dry_run_required=false&approval_id=a1&operator_id=o1&broker_confirmation_id=b1&warnings_acknowledged=true&max_daily_loss=1000&current_daily_loss=10&max_orders_per_day=5&orders_today=1&max_quantity=100&requested_quantity=10"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_permitted"] is True
    assert payload["status"] == "PERMITTED"
    assert payload["blockers"] == []
    assert payload["mode"] == "PAPER"
    assert payload["execution_mode_api_parse"]["mode"] == "PAPER"
    assert payload["execution_mode_api_parse"]["invalid_mode"] is False
    assert payload["broker_api_allowed"] is False
    assert payload["real_order_allowed"] is False
    assert payload["audit"]["top_executable_candidate_id"] == "c1"
    assert payload["safety_visibility_only"] is True
    assert payload["is_order_action"] is False


def test_execution_safety_api_rejects_invalid_mode_and_never_falls_back_to_paper(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _allowed_artifacts(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/execution-safety?mode=REAL&dry_run_required=false&approval_id=a1&operator_id=o1&broker_confirmation_id=b1&warnings_acknowledged=true&max_daily_loss=1000&current_daily_loss=10&max_orders_per_day=5&orders_today=1&max_quantity=100&requested_quantity=10"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "SIM"
    assert payload["execution_permitted"] is False
    assert payload["status"] == "BLOCKED"
    assert "INVALID_EXECUTION_MODE" in payload["blockers"]
    assert "EXECUTION_MODE_FORCED_TO_SIM" in payload["warnings"]
    assert payload["execution_mode_api_parse"]["raw_mode"] == "REAL"
    assert payload["execution_mode_api_parse"]["invalid_mode"] is True
    assert payload["paper_order_allowed"] is False
    assert payload["broker_api_allowed"] is False
    assert payload["real_order_allowed"] is False
    assert payload["is_order_action"] is False


def test_execution_safety_api_live_requires_explicit_live_readiness_flags(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _allowed_artifacts(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/execution-safety?mode=LIVE&dry_run_required=false&approval_id=a1&operator_id=o1&broker_confirmation_id=b1&warnings_acknowledged=true"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "LIVE"
    assert payload["execution_permitted"] is False
    assert "LIVE_REAL_BROKER_ADAPTER_NOT_ENABLED" in payload["blockers"]
    assert "LIVE_BROKER_READINESS_REQUIRED" in payload["blockers"]
    assert "LIVE_RISK_READINESS_REQUIRED" in payload["blockers"]
    assert "LIVE_KILL_SWITCH_READINESS_REQUIRED" in payload["blockers"]
    assert payload["broker_api_allowed"] is False
    assert payload["real_order_allowed"] is False
    assert payload["execution_mode_api_parse"]["mode"] == "LIVE"


def test_execution_safety_api_kill_switch_blocks_even_with_valid_preview(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _allowed_artifacts(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/execution-safety?mode=PAPER&kill_switch_enabled=true&dry_run_required=false&approval_id=a1&operator_id=o1&broker_confirmation_id=b1&warnings_acknowledged=true"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_permitted"] is False
    assert "KILL_SWITCH_ENABLED" in payload["blockers"]
    assert payload["is_order_action"] is False

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.execution_safety_response_contract import (
    execution_safety_response_schema_contract,
    validate_execution_safety_response_contract,
)
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


def test_execution_safety_response_schema_contract_lists_required_safety_fields():
    contract = execution_safety_response_schema_contract()

    assert contract["contract_type"] == "EXECUTION_SAFETY_RESPONSE_CONTRACT"
    assert contract["schema_version"] == "1.0"
    required = set(contract["required_keys"])
    assert {
        "execution_permitted",
        "mode",
        "status",
        "blockers",
        "warnings",
        "audit",
        "simulated_order_allowed",
        "paper_order_allowed",
        "broker_api_allowed",
        "real_order_allowed",
        "is_order_action",
        "execution_mode_api_parse",
        "top_executable",
        "readiness_records_checked",
        "safety_visibility_only",
    }.issubset(required)
    assert contract["supported_modes"] == ["SIM", "PAPER", "LIVE"]
    assert contract["always_false_flags"] == ["is_order_action"]
    assert "broker_api_allowed" in contract["invalid_mode_false_flags"]
    assert "real_order_allowed" in contract["invalid_mode_false_flags"]


def test_execution_safety_response_contract_accepts_default_blocked_endpoint_payload(tmp_path, monkeypatch):
    import api.server as server

    monkeypatch.setattr(server, "_runtime_root", lambda: tmp_path / ".runtime")
    client = TestClient(app)

    response = client.get("/execution-safety")

    assert response.status_code == 200
    result = validate_execution_safety_response_contract(response.json())
    assert result["valid"] is True
    assert result["missing_keys"] == []
    assert result["execution_mode_parse_missing_keys"] == []
    assert result["type_errors"] == []
    assert result["safe_flag_violations"] == []


def test_execution_safety_response_contract_accepts_invalid_mode_blocked_endpoint_payload(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _allowed_artifacts(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/execution-safety?mode=REAL&dry_run_required=false&approval_id=a1&operator_id=o1&broker_confirmation_id=b1&warnings_acknowledged=true&max_daily_loss=1000&current_daily_loss=10&max_orders_per_day=5&orders_today=1&max_quantity=100&requested_quantity=10"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_permitted"] is False
    assert payload["broker_api_allowed"] is False
    assert payload["real_order_allowed"] is False
    result = validate_execution_safety_response_contract(payload)
    assert result["valid"] is True
    assert result["safe_flag_violations"] == []


def test_execution_safety_response_contract_detects_missing_and_unsafe_fields():
    payload = {
        "execution_permitted": True,
        "mode": "LIVE",
        "status": "PERMITTED",
        "blockers": [],
        "warnings": [],
        "audit": {},
        "requires_manual_approval": False,
        "simulated_order_allowed": False,
        "paper_order_allowed": False,
        "broker_api_allowed": True,
        "real_order_allowed": True,
        "is_order_action": True,
        "execution_mode_api_parse": {
            "mode": "SIM",
            "invalid_mode": True,
            "supported_modes": ["SIM", "PAPER", "LIVE"],
            "blockers": ["INVALID_EXECUTION_MODE"],
            "warnings": ["EXECUTION_MODE_FORCED_TO_SIM"],
            "is_order_action": False,
        },
        "top_executable": {},
        "readiness_records_checked": 1,
        "safety_visibility_only": True,
    }

    result = validate_execution_safety_response_contract(payload)

    assert result["valid"] is False
    assert "raw_mode" in result["execution_mode_parse_missing_keys"]
    assert "is_order_action must be false" in result["safe_flag_violations"]
    assert "execution_permitted must be false when invalid_mode=true" in result["safe_flag_violations"]
    assert "broker_api_allowed must be false when invalid_mode=true" in result["safe_flag_violations"]
    assert "real_order_allowed must be false when invalid_mode=true" in result["safe_flag_violations"]

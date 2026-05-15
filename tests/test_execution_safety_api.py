from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import app


def _allowed_artifacts(tmp_path):
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    (runtime_root / "top_opportunities_latest.json").write_text(
        '{"top_executable_opportunities":[{"candidate_id":"c1","symbol":"NIFTY","strategy":"test","score":90,"confidence":90,"permission":"EXECUTE","final_action":"EXECUTE"}]}',
        encoding="utf-8",
    )
    (runtime_root / "broker_contract_readiness_latest.json").write_text(
        '{"records":[{"candidate_id":"c1","status":"RESOLVED_EXACT","instrument":{"tradingsymbol":"NIFTY","instrument_token":"1"}}]}',
        encoding="utf-8",
    )
    (runtime_root / "market_readiness_latest.json").write_text(
        '{"records":[{"candidate_id":"c1","status":"READY","quote_age_seconds":1,"depth_age_seconds":1,"spread_pct":1,"slippage_budget_pct":2}]}',
        encoding="utf-8",
    )
    (runtime_root / "risk_readiness_latest.json").write_text(
        '{"records":[{"candidate_id":"c1","status":"READY","allowed":true}]}',
        encoding="utf-8",
    )
    return runtime_root


def test_execution_safety_api_blocks_by_default(tmp_path, monkeypatch):
    import api.server as server

    monkeypatch.setattr(server, "_runtime_root", lambda: tmp_path / ".runtime")
    client = TestClient(app)

    response = client.get("/execution-safety")

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_permitted"] is False
    assert payload["status"] == "BLOCKED"
    assert "DRY_RUN_REQUIRED" in payload["blockers"]
    assert "MANUAL_APPROVAL_REQUIRED" in payload["blockers"]
    assert "BROKER_CONFIRMATION_REQUIRED" in payload["blockers"]
    assert payload["is_order_action"] is False
    assert payload["safety_visibility_only"] is True


def test_execution_safety_api_can_show_permitted_paper_preview(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _allowed_artifacts(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/execution-safety?dry_run_required=false&approval_id=a1&operator_id=o1&broker_confirmation_id=b1&warnings_acknowledged=true&max_daily_loss=1000&current_daily_loss=10&max_orders_per_day=5&orders_today=1&max_quantity=100&requested_quantity=10"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_permitted"] is True
    assert payload["status"] == "PERMITTED"
    assert payload["blockers"] == []
    assert payload["mode"] == "PAPER"
    assert payload["audit"]["top_executable_candidate_id"] == "c1"
    assert payload["safety_visibility_only"] is True
    assert payload["is_order_action"] is False


def test_execution_safety_api_kill_switch_blocks_even_with_valid_preview(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = _allowed_artifacts(tmp_path)
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get(
        "/execution-safety?kill_switch_enabled=true&dry_run_required=false&approval_id=a1&operator_id=o1&broker_confirmation_id=b1&warnings_acknowledged=true"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_permitted"] is False
    assert "KILL_SWITCH_ENABLED" in payload["blockers"]
    assert payload["is_order_action"] is False

from __future__ import annotations

import json

from paper_trading.pipeline import paper_trading_pipeline_schema_contract, run_paper_trading_pipeline


def _top(candidate_id="c1", **selected_overrides):
    selected = {
        "candidate_id": candidate_id,
        "symbol": "NIFTY26MAY25500CE",
        "tradingsymbol": "NIFTY26MAY25500CE",
        "instrument_token": 12345,
        "transaction_type": "BUY",
        "quantity": 10,
        "order_type": "LIMIT",
        "product": "MIS",
        "price": 100.5,
        "trigger_price": 95.0,
        "strategy": "orb_retest",
        "quality_score": 91.0,
        "is_order": False,
    }
    selected.update(selected_overrides)
    return {"status": "SELECTED", "selected": selected, "is_order_action": False}


def _safety(**overrides):
    payload = {
        "execution_permitted": True,
        "status": "PERMITTED",
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "safety_visibility_only": True,
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def _readiness(**overrides):
    payload = {
        "candidate_id": "c1",
        "readiness_status": "RESOLVED_EXACT",
        "resolved": True,
        "instrument_token": 12345,
        "fallback_used": False,
        "blockers": [],
        "warnings": [],
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _market_data(**overrides):
    payload = {
        "guard_type": "MARKET_SESSION_EXPIRY_CONTEXT_GUARD",
        "status": "READY",
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "session_open": True,
        "expiry_valid": True,
        "blockers": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def _instrument_health(**overrides):
    payload = {
        "panel_type": "INSTRUMENT_RESOLUTION_HEALTH_PANEL",
        "status": "HEALTHY",
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "summary": {"resolved_count": 1, "unresolved_count": 0},
        "blockers": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def _quote(**overrides):
    payload = {
        "source": "CONTROLLED_QUOTE",
        "ts_epoch": 104.0,
        "ask": 100.0,
        "bid": 99.5,
        "last": 99.75,
        "available_quantity": 10,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _run(**overrides):
    payload = {
        "cycle_id": "cycle-1",
        "top_executable": _top(),
        "execution_safety": _safety(),
        "readiness": _readiness(),
        "market_data": _market_data(),
        "instrument_health": _instrument_health(),
        "quote": _quote(),
        "ts_epoch": 100.0,
        "now_epoch": 105.0,
    }
    payload.update(overrides)
    return run_paper_trading_pipeline(**payload).to_dict()


def test_pipeline_schema_contract_is_safe_and_scoped():
    contract = paper_trading_pipeline_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["pipeline_type"] == "IN_MEMORY_PAPER_TRADING_PIPELINE"
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "no_journal_append" in contract["scope_boundary"]
    assert "no_runtime_wiring" in contract["scope_boundary"]
    assert "no_broker_execution" in contract["scope_boundary"]
    assert "COMPLETED" in contract["statuses"]
    assert "BLOCKED" in contract["statuses"]


def test_valid_minimal_paper_cycle_returns_completed():
    payload = _run()

    assert payload["status"] == "COMPLETED"
    assert payload["completed"] is True
    assert payload["cycle_id"] == "cycle-1"
    assert payload["candidate_id"] == "c1"
    assert payload["strategy_id"] == "orb_retest"
    assert payload["event_count"] == 4
    assert [event["event_sequence"] for event in payload["events"]] == [1, 2, 3, 4]
    assert [event["event_type"] for event in payload["events"]] == [
        "PAPER_ORDER_INTENT_CREATED",
        "PAPER_ORDER_ACCEPTED",
        "PAPER_ORDER_OPENED",
        "PAPER_ORDER_FILLED",
    ]
    assert payload["stages"]["ordering"]["status"] == "VALID"
    assert payload["stages"]["reducer"]["status"] == "REDUCED"
    assert payload["state"]["summary"]["event_count"] == 4
    assert payload["paper_only"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_missing_required_input_returns_blocked():
    payload = _run(cycle_id="")

    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    assert payload["blockers"] == ["PAPER_PIPELINE_CYCLE_ID_REQUIRED"]


def test_unsafe_order_action_input_returns_blocked():
    payload = _run(top_executable=_top(is_order_action=True))

    assert payload["status"] == "BLOCKED"
    assert any("UNSAFE_ORDER_ACTION_FLAG" in blocker for blocker in payload["blockers"])


def test_broker_api_called_input_returns_blocked():
    payload = _run(execution_safety=_safety(broker_api_called=True))

    assert payload["status"] == "BLOCKED"
    assert any("BROKER_API_CALLED" in blocker for blocker in payload["blockers"])


def test_real_order_id_input_returns_blocked():
    payload = _run(quote=_quote(real_order_id="real-123"))

    assert payload["status"] == "BLOCKED"
    assert any("REAL_ORDER_ID_PRESENT" in blocker for blocker in payload["blockers"])


def test_blocked_fill_simulation_returns_blocked():
    payload = _run(quote=_quote(ts_epoch=1.0), now_epoch=105.0, max_quote_age_sec=5.0)

    assert payload["status"] == "BLOCKED"
    assert any("FILL" in blocker for blocker in payload["blockers"])
    assert any("STALE" in blocker for blocker in payload["blockers"])


def test_invalid_intent_stage_returns_blocked():
    payload = _run(top_executable={"status": "EMPTY", "selected": None, "is_order_action": False})

    assert payload["status"] == "BLOCKED"
    assert any("INTENT" in blocker for blocker in payload["blockers"])


def test_market_data_blocker_returns_blocked_before_events():
    payload = _run(market_data=_market_data(status="BLOCKED_STALE_SPOT"))

    assert payload["status"] == "BLOCKED"
    assert any("MARKET_DATA" in blocker for blocker in payload["blockers"])
    assert payload["events"] == []


def test_pipeline_output_has_no_order_controls():
    payload_text = json.dumps(_run()).lower()

    assert "submit" not in payload_text
    assert "modify" not in payload_text
    assert "cancel_order" not in payload_text
    assert "exit_order" not in payload_text
    assert "place_order" not in payload_text


def test_same_input_produces_same_pipeline_result():
    first = _run()
    second = _run()

    assert first["events"] == second["events"]
    assert first["state"] == second["state"]
    assert first["stages"]["ordering"] == second["stages"]["ordering"]


def test_partial_fill_still_completes_with_partial_event():
    payload = _run(quote=_quote(available_quantity=4))

    assert payload["status"] == "COMPLETED"
    assert payload["events"][-1]["event_type"] == "PAPER_ORDER_PARTIALLY_FILLED"
    assert payload["state"]["summary"]["open_order_count"] == 1


def test_no_fill_completes_without_terminal_fill_event():
    payload = _run(quote=_quote(ask=101.0, available_quantity=10))

    assert payload["status"] == "COMPLETED"
    assert payload["event_count"] == 3
    assert payload["events"][-1]["event_type"] == "PAPER_ORDER_OPENED"
    assert payload["stages"]["fill"]["status"] == "NO_FILL"


def test_pipeline_does_not_mutate_established_contracts():
    contract = paper_trading_pipeline_schema_contract()

    assert contract["upstream_contracts"]["intent"]["bridge_type"] == "PAPER_ORDER_INTENT_BRIDGE"
    assert contract["upstream_contracts"]["lifecycle"]["lifecycle_type"] == "PAPER_ORDER_LIFECYCLE"
    assert contract["upstream_contracts"]["fill"]["simulation_type"] == "PAPER_FILL_SIMULATION_ENGINE"
    assert contract["upstream_contracts"]["ordering"]["guard_type"] == "PAPER_EVENT_ORDERING_IDEMPOTENCY_GUARD"
    assert contract["upstream_contracts"]["reducer"]["reducer_type"] == "DETERMINISTIC_PAPER_STATE_REDUCER"

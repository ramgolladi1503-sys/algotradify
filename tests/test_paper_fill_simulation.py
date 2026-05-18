from __future__ import annotations

from paper_trading import (
    build_paper_order_intent,
    build_paper_order_lifecycle_event,
    paper_fill_simulation_schema_contract,
    simulate_paper_fill,
)


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
    }
    payload.update(overrides)
    return payload


def _market_data(**overrides):
    payload = {
        "guard_type": "MARKET_SESSION_EXPIRY_CONTEXT_GUARD",
        "status": "READY",
        "read_only": True,
        "is_order_action": False,
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
        "summary": {"resolved_count": 1, "unresolved_count": 0},
        "blockers": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def _paper_intent_payload(**selected_overrides):
    result = build_paper_order_intent(
        top_executable=_top(**selected_overrides),
        execution_safety=_safety(),
        readiness=_readiness(),
        market_data=_market_data(),
        instrument_health=_instrument_health(),
        ts_epoch=100.0,
    )
    assert result.created is True
    return result.to_dict()["intent"]


def _open_event(intent=None):
    intent = intent or _paper_intent_payload()
    created = build_paper_order_lifecycle_event(intent=intent, requested_status="CREATED", ts_epoch=101.0)
    accepted = build_paper_order_lifecycle_event(intent=intent, previous_event=created.to_dict()["event"], requested_status="ACCEPTED", ts_epoch=102.0)
    opened = build_paper_order_lifecycle_event(intent=intent, previous_event=accepted.to_dict()["event"], requested_status="OPEN", ts_epoch=103.0)
    assert opened.created is True
    return opened.to_dict()["event"]


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


def test_paper_fill_simulation_schema_contract_is_safe():
    contract = paper_fill_simulation_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["simulation_type"] == "PAPER_FILL_SIMULATION_ENGINE"
    assert "PAPER_ORDER_INTENT" in contract["consumes"]
    assert "PAPER_ORDER_LIFECYCLE_EVENT" in contract["consumes"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "FULL_FILL" in contract["statuses"]
    assert "PARTIAL_FILL" in contract["statuses"]
    assert "NO_FILL" in contract["statuses"]
    assert "REJECTED_FILL" in contract["statuses"]
    assert "EXPIRED_FILL" in contract["statuses"]


def test_paper_fill_simulation_full_fill_from_controlled_quote():
    intent = _paper_intent_payload()
    result = simulate_paper_fill(
        intent=intent,
        previous_event=_open_event(intent),
        quote=_quote(ask=100.0, available_quantity=10),
        now_epoch=105.0,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["simulated"] is True
    assert payload["status"] == "FULL_FILL"
    assert payload["fill_quantity"] == 10
    assert payload["cumulative_filled_quantity"] == 10
    assert payload["remaining_quantity"] == 0
    assert payload["fill_price"] == 100.0
    assert payload["lifecycle_event"]["status"] == "FILLED"
    assert payload["lifecycle_event"]["terminal"] is True
    assert payload["paper_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["lifecycle_event"]["paper_only"] is True
    assert payload["lifecycle_event"]["is_order_action"] is False
    assert payload["lifecycle_event"]["broker_api_called"] is False
    assert payload["lifecycle_event"]["real_order_id"] is None


def test_paper_fill_simulation_partial_fill_from_limited_controlled_liquidity():
    intent = _paper_intent_payload()
    result = simulate_paper_fill(
        intent=intent,
        previous_event=_open_event(intent),
        quote=_quote(ask=100.0, available_quantity=4),
        now_epoch=105.0,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["simulated"] is True
    assert payload["status"] == "PARTIAL_FILL"
    assert payload["fill_quantity"] == 4
    assert payload["cumulative_filled_quantity"] == 4
    assert payload["remaining_quantity"] == 6
    assert payload["lifecycle_event"]["status"] == "PARTIALLY_FILLED"
    assert payload["lifecycle_event"]["terminal"] is False
    assert payload["lifecycle_event"]["filled_quantity"] == 4
    assert payload["lifecycle_event"]["remaining_quantity"] == 6


def test_paper_fill_simulation_no_fill_when_limit_not_marketable():
    intent = _paper_intent_payload(price=100.5)
    result = simulate_paper_fill(
        intent=intent,
        previous_event=_open_event(intent),
        quote=_quote(ask=101.0, available_quantity=10),
        now_epoch=105.0,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["simulated"] is True
    assert payload["status"] == "NO_FILL"
    assert payload["lifecycle_event"] is None
    assert payload["fill_quantity"] == 0
    assert payload["cumulative_filled_quantity"] == 0
    assert payload["remaining_quantity"] == 10
    assert "NO_MARKETABLE_PRICE_FROM_CONTROLLED_QUOTE" in payload["warnings"]
    assert payload["broker_api_called"] is False


def test_paper_fill_simulation_rejected_fill_from_controlled_input():
    intent = _paper_intent_payload()
    result = simulate_paper_fill(
        intent=intent,
        previous_event=_open_event(intent),
        quote=_quote(status="REJECTED", reject_reason="controlled paper rejection"),
        now_epoch=105.0,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["simulated"] is True
    assert payload["status"] == "REJECTED_FILL"
    assert payload["fill_quantity"] == 0
    assert payload["remaining_quantity"] == 10
    assert payload["lifecycle_event"]["status"] == "REJECTED"
    assert payload["lifecycle_event"]["terminal"] is True
    assert payload["lifecycle_event"]["reason"] == "controlled paper rejection"
    assert payload["lifecycle_event"]["broker_api_called"] is False


def test_paper_fill_simulation_expired_fill_from_controlled_input():
    intent = _paper_intent_payload()
    result = simulate_paper_fill(
        intent=intent,
        previous_event=_open_event(intent),
        quote=_quote(status="EXPIRED"),
        now_epoch=105.0,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["simulated"] is True
    assert payload["status"] == "EXPIRED_FILL"
    assert payload["lifecycle_event"]["status"] == "EXPIRED"
    assert payload["lifecycle_event"]["terminal"] is True
    assert payload["real_order_id"] is None
    assert payload["lifecycle_event"]["real_order_id"] is None


def test_paper_fill_simulation_blocks_stale_quote():
    intent = _paper_intent_payload()
    result = simulate_paper_fill(
        intent=intent,
        previous_event=_open_event(intent),
        quote=_quote(ts_epoch=90.0),
        now_epoch=105.0,
        max_quote_age_sec=5.0,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["simulated"] is False
    assert payload["status"] == "BLOCKED"
    assert "CONTROLLED_QUOTE_STALE" in payload["blockers"]
    assert payload["lifecycle_event"] is None
    assert payload["evidence"]["quote_age_sec"] == 15.0
    assert payload["broker_api_called"] is False


def test_paper_fill_simulation_blocks_unsafe_intent():
    intent = _paper_intent_payload()
    event = _open_event(intent)
    intent["paper_only"] = False
    intent["broker_api_called"] = True

    result = simulate_paper_fill(
        intent=intent,
        previous_event=event,
        quote=_quote(),
        now_epoch=105.0,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["simulated"] is False
    assert payload["status"] == "BLOCKED"
    assert "PAPER_INTENT_NOT_PAPER_ONLY" in payload["blockers"]
    assert "PAPER_INTENT_BROKER_API_CALLED" in payload["blockers"]
    assert payload["paper_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_paper_fill_simulation_blocks_non_controlled_quote_source():
    intent = _paper_intent_payload()
    result = simulate_paper_fill(
        intent=intent,
        previous_event=_open_event(intent),
        quote=_quote(source="LIVE_BROKER_QUOTE"),
        now_epoch=105.0,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["simulated"] is False
    assert "CONTROLLED_QUOTE_SOURCE_REQUIRED" in payload["blockers"]
    assert payload["evidence"]["controlled_quote_only"] is True


def test_paper_fill_simulation_blocks_when_order_not_open():
    intent = _paper_intent_payload()
    created = build_paper_order_lifecycle_event(intent=intent, requested_status="CREATED", ts_epoch=101.0)

    result = simulate_paper_fill(
        intent=intent,
        previous_event=created.to_dict()["event"],
        quote=_quote(),
        now_epoch=105.0,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["simulated"] is False
    assert "PAPER_ORDER_NOT_OPEN_FOR_FILL_SIMULATION" in payload["blockers"]
    assert payload["lifecycle_event"] is None

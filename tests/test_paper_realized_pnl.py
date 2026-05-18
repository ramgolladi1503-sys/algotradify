from __future__ import annotations

from paper_trading import (
    build_paper_order_intent,
    build_paper_order_lifecycle_event,
    build_paper_position_ledger,
    build_paper_realized_pnl,
    paper_realized_pnl_schema_contract,
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


def _open_event(intent):
    created = build_paper_order_lifecycle_event(intent=intent, requested_status="CREATED", ts_epoch=101.0)
    accepted = build_paper_order_lifecycle_event(intent=intent, previous_event=created.to_dict()["event"], requested_status="ACCEPTED", ts_epoch=102.0)
    opened = build_paper_order_lifecycle_event(intent=intent, previous_event=accepted.to_dict()["event"], requested_status="OPEN", ts_epoch=103.0)
    assert opened.created is True
    return opened.to_dict()["event"]


def _fill_event(intent, previous_event, status="FILLED", filled_quantity=10, price=100.0, ts_epoch=104.0):
    fill = build_paper_order_lifecycle_event(
        intent=intent,
        previous_event=previous_event,
        requested_status=status,
        filled_quantity=filled_quantity,
        average_fill_price=price,
        ts_epoch=ts_epoch,
    )
    assert fill.created is True
    return fill.to_dict()["event"]


def _opened_long_ledger(quantity=10, price=100.0):
    buy_intent = _paper_intent_payload(transaction_type="BUY", quantity=quantity)
    buy_event = _fill_event(buy_intent, _open_event(buy_intent), status="FILLED", filled_quantity=quantity, price=price)
    ledger_result = build_paper_position_ledger(intent=buy_intent, lifecycle_event=buy_event, ts_epoch=104.0)
    assert ledger_result.updated is True
    return ledger_result.to_dict()["ledger"]


def _opened_short_ledger(quantity=5, price=200.0):
    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=quantity)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=quantity, price=price)
    ledger_result = build_paper_position_ledger(intent=sell_intent, lifecycle_event=sell_event, ts_epoch=104.0)
    assert ledger_result.updated is True
    return ledger_result.to_dict()["ledger"]


def test_paper_realized_pnl_schema_contract_is_safe():
    contract = paper_realized_pnl_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["ledger_type"] == "PAPER_REALIZED_PNL_LEDGER"
    assert "PAPER_POSITION_LEDGER" in contract["consumes"]
    assert "PAPER_ORDER_INTENT" in contract["consumes"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "realized_pnl" in contract["required_event_keys"]
    assert "total_realized_pnl" in contract["required_summary_keys"]


def test_paper_realized_pnl_partial_close_long_position():
    previous_ledger = _opened_long_ledger(quantity=10, price=100.0)
    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=4)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=4, price=110.0)

    result = build_paper_realized_pnl(
        previous_position_ledger=previous_ledger,
        intent=sell_intent,
        lifecycle_event=sell_event,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["updated"] is True
    assert payload["status"] == "REALIZED"
    assert payload["realized_quantity"] == 4
    assert payload["realized_pnl"] == 40.0
    assert payload["event"]["previous_net_quantity"] == 10
    assert payload["event"]["signed_delta_quantity"] == -4
    assert payload["ledger"]["summary"]["total_realized_pnl"] == 40.0
    assert payload["paper_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["event"]["real_order_id"] is None


def test_paper_realized_pnl_full_close_short_position():
    previous_ledger = _opened_short_ledger(quantity=5, price=200.0)
    buy_intent = _paper_intent_payload(transaction_type="BUY", quantity=5)
    buy_event = _fill_event(buy_intent, _open_event(buy_intent), status="FILLED", filled_quantity=5, price=180.0)

    result = build_paper_realized_pnl(
        previous_position_ledger=previous_ledger,
        intent=buy_intent,
        lifecycle_event=buy_event,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["updated"] is True
    assert payload["realized_quantity"] == 5
    assert payload["realized_pnl"] == 100.0
    assert payload["event"]["previous_net_quantity"] == -5
    assert payload["event"]["signed_delta_quantity"] == 5
    assert payload["ledger"]["summary"]["winning_event_count"] == 1


def test_paper_realized_pnl_reversal_realizes_only_closed_quantity():
    previous_ledger = _opened_long_ledger(quantity=5, price=100.0)
    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=10)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=10, price=90.0)

    result = build_paper_realized_pnl(
        previous_position_ledger=previous_ledger,
        intent=sell_intent,
        lifecycle_event=sell_event,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["updated"] is True
    assert payload["status"] == "REALIZED"
    assert payload["realized_quantity"] == 5
    assert payload["realized_pnl"] == -50.0
    assert payload["event"]["signed_delta_quantity"] == -10
    assert payload["ledger"]["summary"]["losing_event_count"] == 1


def test_paper_realized_pnl_no_realized_change_for_same_side_increase():
    previous_ledger = _opened_long_ledger(quantity=5, price=100.0)
    buy_intent = _paper_intent_payload(transaction_type="BUY", quantity=5)
    buy_event = _fill_event(buy_intent, _open_event(buy_intent), status="FILLED", filled_quantity=5, price=102.0)

    result = build_paper_realized_pnl(
        previous_position_ledger=previous_ledger,
        intent=buy_intent,
        lifecycle_event=buy_event,
        ts_epoch=105.0,
    )
    payload = result.to_dict()

    assert payload["updated"] is False
    assert payload["status"] == "NO_REALIZED_CHANGE"
    assert payload["realized_quantity"] == 0
    assert payload["realized_pnl"] == 0.0
    assert "FILL_DID_NOT_REDUCE_EXISTING_POSITION" in payload["warnings"]
    assert len(payload["ledger"]["applied_fill_keys"]) == 1


def test_paper_realized_pnl_idempotent_duplicate_fill_key():
    previous_ledger = _opened_long_ledger(quantity=10, price=100.0)
    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=4)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=4, price=110.0)
    first = build_paper_realized_pnl(previous_position_ledger=previous_ledger, intent=sell_intent, lifecycle_event=sell_event, ts_epoch=105.0)

    duplicate = build_paper_realized_pnl(
        previous_position_ledger=previous_ledger,
        intent=sell_intent,
        lifecycle_event=sell_event,
        previous_realized_ledger=first.to_dict()["ledger"],
        ts_epoch=106.0,
    )
    payload = duplicate.to_dict()

    assert first.updated is True
    assert payload["updated"] is False
    assert payload["status"] == "NO_REALIZED_CHANGE"
    assert "DUPLICATE_REALIZED_PNL_FILL_KEY" in payload["warnings"]
    assert payload["ledger"]["summary"]["event_count"] == 1
    assert payload["ledger"]["summary"]["total_realized_pnl"] == 40.0


def test_paper_realized_pnl_ignores_non_fill_lifecycle_event():
    previous_ledger = _opened_long_ledger(quantity=10, price=100.0)
    intent = _paper_intent_payload(transaction_type="SELL", quantity=4)
    opened = _open_event(intent)

    result = build_paper_realized_pnl(previous_position_ledger=previous_ledger, intent=intent, lifecycle_event=opened, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["updated"] is False
    assert payload["status"] == "NO_REALIZED_CHANGE"
    assert "NON_FILL_LIFECYCLE_EVENT_IGNORED" in payload["warnings"]
    assert payload["ledger"]["summary"]["total_realized_pnl"] == 0.0


def test_paper_realized_pnl_blocks_missing_price_inputs():
    previous_ledger = _opened_long_ledger(quantity=10, price=100.0)
    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=4)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=4, price=110.0)
    sell_event["average_fill_price"] = None

    result = build_paper_realized_pnl(previous_position_ledger=previous_ledger, intent=sell_intent, lifecycle_event=sell_event, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["updated"] is False
    assert payload["status"] == "BLOCKED"
    assert "REALIZED_PNL_PRICE_INPUT_REQUIRED" in payload["blockers"]
    assert payload["ledger"]["summary"]["event_count"] == 0


def test_paper_realized_pnl_blocks_unsafe_position_ledger_flags():
    previous_ledger = _opened_long_ledger(quantity=10, price=100.0)
    previous_ledger["broker_api_called"] = True
    previous_ledger["real_order_id"] = "real-123"
    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=4)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=4, price=110.0)

    result = build_paper_realized_pnl(previous_position_ledger=previous_ledger, intent=sell_intent, lifecycle_event=sell_event, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["updated"] is False
    assert payload["status"] == "BLOCKED"
    assert "PREVIOUS_PAPER_POSITION_LEDGER_BROKER_API_CALLED" in payload["blockers"]
    assert "PREVIOUS_PAPER_POSITION_LEDGER_REAL_ORDER_ID_PRESENT" in payload["blockers"]
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_paper_realized_pnl_blocks_unsafe_lifecycle_event_flags():
    previous_ledger = _opened_long_ledger(quantity=10, price=100.0)
    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=4)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=4, price=110.0)
    sell_event["is_order_action"] = True
    sell_event["real_order_id"] = "real-123"

    result = build_paper_realized_pnl(previous_position_ledger=previous_ledger, intent=sell_intent, lifecycle_event=sell_event, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["updated"] is False
    assert "PAPER_ORDER_LIFECYCLE_ORDER_FLAG_UNSAFE" in payload["blockers"]
    assert "PAPER_ORDER_LIFECYCLE_REAL_ORDER_ID_PRESENT" in payload["blockers"]
    assert payload["ledger"]["broker_api_called"] is False


def test_paper_realized_pnl_blocks_cumulative_fill_regression():
    previous_ledger = _opened_long_ledger(quantity=10, price=100.0)
    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=4)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=4, price=110.0)
    previous_ledger["order_fills"][sell_event["paper_order_id"]] = 6

    result = build_paper_realized_pnl(previous_position_ledger=previous_ledger, intent=sell_intent, lifecycle_event=sell_event, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["updated"] is False
    assert payload["status"] == "BLOCKED"
    assert "PAPER_FILL_CUMULATIVE_REGRESSION" in payload["blockers"]

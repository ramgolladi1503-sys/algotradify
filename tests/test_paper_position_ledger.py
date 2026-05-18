from __future__ import annotations

from paper_trading import (
    build_paper_order_intent,
    build_paper_order_lifecycle_event,
    build_paper_position_ledger,
    paper_position_ledger_schema_contract,
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


def test_paper_position_ledger_schema_contract_is_safe():
    contract = paper_position_ledger_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["ledger_type"] == "PAPER_POSITION_LEDGER"
    assert "PAPER_ORDER_INTENT" in contract["consumes"]
    assert "PAPER_ORDER_LIFECYCLE_EVENT" in contract["consumes"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "positions" in contract["required_ledger_keys"]
    assert "order_fills" in contract["required_ledger_keys"]
    assert "average_entry_price" in contract["required_position_keys"]


def test_paper_position_ledger_opens_long_position_from_full_buy_fill():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10)
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=100.0)

    result = build_paper_position_ledger(intent=intent, lifecycle_event=event, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["updated"] is True
    assert payload["status"] == "POSITION_OPENED"
    assert payload["delta_quantity"] == 10
    assert payload["signed_delta_quantity"] == 10
    assert payload["position"]["net_quantity"] == 10
    assert payload["position"]["side"] == "LONG"
    assert payload["position"]["average_entry_price"] == 100.0
    assert payload["ledger"]["order_fills"][event["paper_order_id"]] == 10
    assert payload["paper_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["position"]["real_order_id"] is None


def test_paper_position_ledger_applies_only_incremental_quantity_for_partial_fills():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10)
    opened = _open_event(intent)
    partial_4 = _fill_event(intent, opened, status="PARTIALLY_FILLED", filled_quantity=4, price=100.0, ts_epoch=104.0)
    first = build_paper_position_ledger(intent=intent, lifecycle_event=partial_4, ts_epoch=104.0)

    partial_7 = _fill_event(intent, partial_4, status="PARTIALLY_FILLED", filled_quantity=7, price=102.0, ts_epoch=105.0)
    second = build_paper_position_ledger(intent=intent, lifecycle_event=partial_7, previous_ledger=first.to_dict()["ledger"], ts_epoch=105.0)
    payload = second.to_dict()

    assert first.to_dict()["position"]["net_quantity"] == 4
    assert payload["updated"] is True
    assert payload["delta_quantity"] == 3
    assert payload["signed_delta_quantity"] == 3
    assert payload["position"]["net_quantity"] == 7
    assert payload["position"]["average_entry_price"] == 100.857143
    assert payload["ledger"]["order_fills"][partial_7["paper_order_id"]] == 7


def test_paper_position_ledger_does_not_double_count_duplicate_fill_event():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10)
    event = _fill_event(intent, _open_event(intent), status="PARTIALLY_FILLED", filled_quantity=4, price=100.0)
    first = build_paper_position_ledger(intent=intent, lifecycle_event=event, ts_epoch=104.0)
    duplicate = build_paper_position_ledger(intent=intent, lifecycle_event=event, previous_ledger=first.to_dict()["ledger"], ts_epoch=105.0)
    payload = duplicate.to_dict()

    assert payload["updated"] is False
    assert payload["status"] == "NO_POSITION_CHANGE"
    assert payload["delta_quantity"] == 0
    assert payload["ledger"]["positions"]["12345"]["net_quantity"] == 4
    assert "DUPLICATE_OR_ALREADY_APPLIED_FILL_EVENT" in payload["warnings"]


def test_paper_position_ledger_reduces_position_with_sell_fill():
    buy_intent = _paper_intent_payload(transaction_type="BUY", quantity=10)
    buy_event = _fill_event(buy_intent, _open_event(buy_intent), status="FILLED", filled_quantity=10, price=100.0)
    opened = build_paper_position_ledger(intent=buy_intent, lifecycle_event=buy_event, ts_epoch=104.0)

    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=4)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=4, price=105.0)
    reduced = build_paper_position_ledger(intent=sell_intent, lifecycle_event=sell_event, previous_ledger=opened.to_dict()["ledger"], ts_epoch=105.0)
    payload = reduced.to_dict()

    assert payload["updated"] is True
    assert payload["status"] == "POSITION_REDUCED"
    assert payload["signed_delta_quantity"] == -4
    assert payload["position"]["net_quantity"] == 6
    assert payload["position"]["side"] == "LONG"
    assert payload["position"]["average_entry_price"] == 100.0


def test_paper_position_ledger_closes_position_without_pnl():
    buy_intent = _paper_intent_payload(transaction_type="BUY", quantity=10)
    buy_event = _fill_event(buy_intent, _open_event(buy_intent), status="FILLED", filled_quantity=10, price=100.0)
    opened = build_paper_position_ledger(intent=buy_intent, lifecycle_event=buy_event, ts_epoch=104.0)

    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=10)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=10, price=105.0)
    closed = build_paper_position_ledger(intent=sell_intent, lifecycle_event=sell_event, previous_ledger=opened.to_dict()["ledger"], ts_epoch=105.0)
    payload = closed.to_dict()

    assert payload["updated"] is True
    assert payload["status"] == "POSITION_CLOSED"
    assert payload["position"]["net_quantity"] == 0
    assert payload["position"]["side"] == "FLAT"
    assert payload["position"]["average_entry_price"] is None
    assert "pnl" not in payload["position"]
    assert "realized_pnl" not in payload["position"]


def test_paper_position_ledger_reverses_position_without_real_order_id():
    buy_intent = _paper_intent_payload(transaction_type="BUY", quantity=5)
    buy_event = _fill_event(buy_intent, _open_event(buy_intent), status="FILLED", filled_quantity=5, price=100.0)
    opened = build_paper_position_ledger(intent=buy_intent, lifecycle_event=buy_event, ts_epoch=104.0)

    sell_intent = _paper_intent_payload(transaction_type="SELL", quantity=10)
    sell_event = _fill_event(sell_intent, _open_event(sell_intent), status="FILLED", filled_quantity=10, price=99.0)
    reversed_position = build_paper_position_ledger(intent=sell_intent, lifecycle_event=sell_event, previous_ledger=opened.to_dict()["ledger"], ts_epoch=105.0)
    payload = reversed_position.to_dict()

    assert payload["updated"] is True
    assert payload["status"] == "POSITION_REVERSED"
    assert payload["position"]["net_quantity"] == -5
    assert payload["position"]["side"] == "SHORT"
    assert payload["position"]["average_entry_price"] == 99.0
    assert payload["ledger"]["broker_api_called"] is False
    assert payload["ledger"]["real_order_id"] is None


def test_paper_position_ledger_ignores_non_fill_lifecycle_event():
    intent = _paper_intent_payload()
    opened = _open_event(intent)

    result = build_paper_position_ledger(intent=intent, lifecycle_event=opened, ts_epoch=103.0)
    payload = result.to_dict()

    assert payload["updated"] is False
    assert payload["status"] == "NO_POSITION_CHANGE"
    assert payload["position"] is None
    assert payload["ledger"]["positions"] == {}
    assert "NON_FILL_LIFECYCLE_EVENT_IGNORED" in payload["warnings"]


def test_paper_position_ledger_blocks_unsafe_intent_flags():
    intent = _paper_intent_payload()
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=100.0)
    intent["broker_api_called"] = True
    intent["real_order_id"] = "real-123"

    result = build_paper_position_ledger(intent=intent, lifecycle_event=event, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["updated"] is False
    assert payload["status"] == "BLOCKED"
    assert "PAPER_INTENT_BROKER_API_CALLED" in payload["blockers"]
    assert "PAPER_INTENT_REAL_ORDER_ID_PRESENT" in payload["blockers"]
    assert payload["paper_only"] is True
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_paper_position_ledger_blocks_unsafe_lifecycle_event_flags():
    intent = _paper_intent_payload()
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=100.0)
    event["paper_only"] = False
    event["is_order_action"] = True

    result = build_paper_position_ledger(intent=intent, lifecycle_event=event, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["updated"] is False
    assert "PAPER_ORDER_LIFECYCLE_NOT_PAPER_ONLY" in payload["blockers"]
    assert "PAPER_ORDER_LIFECYCLE_ORDER_FLAG_UNSAFE" in payload["blockers"]
    assert payload["ledger"]["is_order_action"] is False


def test_paper_position_ledger_blocks_cumulative_fill_regression():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10)
    opened = _open_event(intent)
    partial_7 = _fill_event(intent, opened, status="PARTIALLY_FILLED", filled_quantity=7, price=100.0, ts_epoch=104.0)
    first = build_paper_position_ledger(intent=intent, lifecycle_event=partial_7, ts_epoch=104.0)

    regressed = dict(partial_7)
    regressed["filled_quantity"] = 4
    result = build_paper_position_ledger(intent=intent, lifecycle_event=regressed, previous_ledger=first.to_dict()["ledger"], ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["updated"] is False
    assert payload["status"] == "BLOCKED"
    assert "PAPER_FILL_CUMULATIVE_REGRESSION" in payload["blockers"]
    assert payload["ledger"]["positions"]["12345"]["net_quantity"] == 7

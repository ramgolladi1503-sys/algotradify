from __future__ import annotations

from paper_trading import (
    build_paper_order_intent,
    build_paper_order_lifecycle_event,
    build_paper_slippage_report,
    paper_slippage_schema_contract,
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
        "price": 100.0,
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


def test_paper_slippage_schema_contract_is_safe():
    contract = paper_slippage_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["report_type"] == "PAPER_SLIPPAGE_FILL_QUALITY"
    assert "PAPER_ORDER_INTENT" in contract["consumes"]
    assert "PAPER_ORDER_LIFECYCLE_EVENT" in contract["consumes"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "slippage_bps" in contract["required_event_keys"]
    assert "weighted_average_slippage_bps" in contract["required_summary_keys"]


def test_paper_slippage_measures_unfavorable_buy_fill():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=101.0)

    result = build_paper_slippage_report(intent=intent, lifecycle_event=event, expected_price=100.0, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["measured"] is True
    assert payload["status"] == "MEASURED"
    assert payload["measured_quantity"] == 10
    assert payload["slippage_per_unit"] == 1.0
    assert payload["slippage_amount"] == 10.0
    assert payload["slippage_bps"] == 100.0
    assert payload["event"]["slippage_quality"] == "UNFAVORABLE"
    assert payload["report"]["summary"]["unfavorable_event_count"] == 1
    assert payload["paper_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["event"]["real_order_id"] is None


def test_paper_slippage_measures_favorable_buy_fill():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=99.5)

    result = build_paper_slippage_report(intent=intent, lifecycle_event=event, expected_price=100.0, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["measured"] is True
    assert payload["slippage_per_unit"] == -0.5
    assert payload["slippage_amount"] == -5.0
    assert payload["slippage_bps"] == -50.0
    assert payload["event"]["slippage_quality"] == "FAVORABLE"
    assert payload["report"]["summary"]["favorable_event_count"] == 1


def test_paper_slippage_measures_unfavorable_sell_fill():
    intent = _paper_intent_payload(transaction_type="SELL", quantity=5, price=200.0)
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=5, price=198.0)

    result = build_paper_slippage_report(intent=intent, lifecycle_event=event, expected_price=200.0, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["measured"] is True
    assert payload["measured_quantity"] == 5
    assert payload["slippage_per_unit"] == 2.0
    assert payload["slippage_amount"] == 10.0
    assert payload["slippage_bps"] == 100.0
    assert payload["event"]["slippage_quality"] == "UNFAVORABLE"


def test_paper_slippage_tracks_incremental_partial_fill_quantity():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    opened = _open_event(intent)
    partial_4 = _fill_event(intent, opened, status="PARTIALLY_FILLED", filled_quantity=4, price=101.0, ts_epoch=104.0)
    first = build_paper_slippage_report(intent=intent, lifecycle_event=partial_4, expected_price=100.0, ts_epoch=104.0)

    partial_7 = _fill_event(intent, partial_4, status="PARTIALLY_FILLED", filled_quantity=7, price=102.0, ts_epoch=105.0)
    second = build_paper_slippage_report(
        intent=intent,
        lifecycle_event=partial_7,
        expected_price=100.0,
        previous_report=first.to_dict()["report"],
        ts_epoch=105.0,
    )
    payload = second.to_dict()

    assert first.to_dict()["measured_quantity"] == 4
    assert payload["measured"] is True
    assert payload["measured_quantity"] == 3
    assert payload["slippage_per_unit"] == 2.0
    assert payload["slippage_amount"] == 6.0
    assert payload["report"]["summary"]["measured_quantity"] == 7
    assert payload["report"]["summary"]["total_slippage_amount"] == 10.0


def test_paper_slippage_is_idempotent_for_duplicate_fill_key():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=101.0)
    first = build_paper_slippage_report(intent=intent, lifecycle_event=event, expected_price=100.0, ts_epoch=105.0)
    duplicate = build_paper_slippage_report(
        intent=intent,
        lifecycle_event=event,
        expected_price=100.0,
        previous_report=first.to_dict()["report"],
        ts_epoch=106.0,
    )
    payload = duplicate.to_dict()

    assert first.measured is True
    assert payload["measured"] is False
    assert payload["status"] == "NO_SLIPPAGE_CHANGE"
    assert "DUPLICATE_SLIPPAGE_FILL_KEY" in payload["warnings"]
    assert payload["report"]["summary"]["event_count"] == 1
    assert payload["report"]["summary"]["total_slippage_amount"] == 10.0


def test_paper_slippage_ignores_non_fill_lifecycle_event():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    opened = _open_event(intent)

    result = build_paper_slippage_report(intent=intent, lifecycle_event=opened, expected_price=100.0, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["measured"] is False
    assert payload["status"] == "NO_FILL"
    assert "NON_FILL_LIFECYCLE_EVENT_IGNORED" in payload["warnings"]
    assert payload["report"]["summary"]["event_count"] == 0


def test_paper_slippage_blocks_missing_expected_price():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10)
    intent["price"] = None
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=101.0)

    result = build_paper_slippage_report(intent=intent, lifecycle_event=event, expected_price=None, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["measured"] is False
    assert payload["status"] == "BLOCKED"
    assert "CONTROLLED_EXPECTED_PRICE_REQUIRED" in payload["blockers"]
    assert payload["broker_api_called"] is False


def test_paper_slippage_blocks_missing_fill_price():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=101.0)
    event["average_fill_price"] = None

    result = build_paper_slippage_report(intent=intent, lifecycle_event=event, expected_price=100.0, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["measured"] is False
    assert payload["status"] == "BLOCKED"
    assert "SLIPPAGE_PRICE_INPUT_REQUIRED" in payload["blockers"]
    assert payload["report"]["summary"]["event_count"] == 0


def test_paper_slippage_blocks_unsafe_intent_flags():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=101.0)
    intent["broker_api_called"] = True
    intent["real_order_id"] = "real-123"

    result = build_paper_slippage_report(intent=intent, lifecycle_event=event, expected_price=100.0, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["measured"] is False
    assert payload["status"] == "BLOCKED"
    assert "PAPER_INTENT_BROKER_API_CALLED" in payload["blockers"]
    assert "PAPER_INTENT_REAL_ORDER_ID_PRESENT" in payload["blockers"]
    assert payload["paper_only"] is True
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_paper_slippage_blocks_unsafe_lifecycle_event_flags():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=101.0)
    event["paper_only"] = False
    event["is_order_action"] = True

    result = build_paper_slippage_report(intent=intent, lifecycle_event=event, expected_price=100.0, ts_epoch=105.0)
    payload = result.to_dict()

    assert payload["measured"] is False
    assert "PAPER_ORDER_LIFECYCLE_NOT_PAPER_ONLY" in payload["blockers"]
    assert "PAPER_ORDER_LIFECYCLE_ORDER_FLAG_UNSAFE" in payload["blockers"]
    assert payload["report"]["is_order_action"] is False


def test_paper_slippage_blocks_cumulative_fill_regression():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    opened = _open_event(intent)
    partial_7 = _fill_event(intent, opened, status="PARTIALLY_FILLED", filled_quantity=7, price=101.0)
    first = build_paper_slippage_report(intent=intent, lifecycle_event=partial_7, expected_price=100.0, ts_epoch=105.0)

    regressed = dict(partial_7)
    regressed["filled_quantity"] = 4
    result = build_paper_slippage_report(
        intent=intent,
        lifecycle_event=regressed,
        expected_price=100.0,
        previous_report=first.to_dict()["report"],
        ts_epoch=106.0,
    )
    payload = result.to_dict()

    assert payload["measured"] is False
    assert payload["status"] == "BLOCKED"
    assert "PAPER_FILL_CUMULATIVE_REGRESSION" in payload["blockers"]
    assert payload["report"]["summary"]["measured_quantity"] == 7


def test_paper_slippage_does_not_emit_pnl_or_broker_fields():
    intent = _paper_intent_payload(transaction_type="BUY", quantity=10, price=100.0)
    event = _fill_event(intent, _open_event(intent), status="FILLED", filled_quantity=10, price=101.0)

    result = build_paper_slippage_report(intent=intent, lifecycle_event=event, expected_price=100.0, ts_epoch=105.0)
    payload = result.to_dict()

    assert "realized_pnl" not in payload["event"]
    assert "unrealized_pnl" not in payload["event"]
    assert "fees" not in payload["event"]
    assert payload["event"]["broker_api_called"] is False
    assert payload["event"]["real_order_id"] is None

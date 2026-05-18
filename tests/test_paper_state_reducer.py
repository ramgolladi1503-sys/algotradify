from __future__ import annotations

from copy import deepcopy

from paper_trading import (
    reduce_paper_events,
    paper_state_reducer_schema_contract,
)


def _event(event_id="event-1", event_type="PAPER_ORDER_INTENT_CREATED", sequence=1, **overrides):
    payload = {
        "schema_version": "1.0",
        "event_id": event_id,
        "cycle_id": "cycle-1",
        "event_sequence": sequence,
        "candidate_id": "candidate-1",
        "strategy_id": "orb_retest",
        "paper_order_intent_id": "intent-1",
        "paper_order_id": "order-1",
        "event_type": event_type,
        "ts_epoch": 100.0 + sequence,
        "idempotency_key": f"cycle-1:{event_id}",
        "payload": {},
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def test_paper_state_reducer_schema_contract_is_safe():
    contract = paper_state_reducer_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["reducer_type"] == "DETERMINISTIC_PAPER_STATE_REDUCER"
    assert contract["consumes"] == ["CANONICAL_PAPER_EVENT_JOURNAL"]
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "orders" in contract["required_state_keys"]
    assert "positions" in contract["required_state_keys"]


def test_reduce_empty_event_list_returns_safe_empty_state():
    result = reduce_paper_events([])
    payload = result.to_dict()

    assert payload["reduced"] is True
    assert payload["status"] == "EMPTY"
    assert payload["state"]["summary"]["event_count"] == 0
    assert payload["state"]["paper_only"] is True
    assert payload["state"]["read_only"] is True
    assert payload["state"]["is_order_action"] is False
    assert payload["state"]["broker_api_called"] is False
    assert payload["state"]["real_order_id"] is None


def test_reduce_order_lifecycle_events_to_terminal_state():
    events = [
        _event("event-1", "PAPER_ORDER_INTENT_CREATED", 1),
        _event("event-2", "PAPER_ORDER_ACCEPTED", 2),
        _event("event-3", "PAPER_ORDER_OPENED", 3),
        _event(
            "event-4",
            "PAPER_ORDER_FILLED",
            4,
            payload={"quantity": 10, "filled_quantity": 10, "remaining_quantity": 0, "average_fill_price": 101.5},
        ),
    ]

    payload = reduce_paper_events(events).to_dict()
    order = payload["state"]["orders"]["order-1"]

    assert payload["reduced"] is True
    assert payload["status"] == "REDUCED"
    assert order["status"] == "FILLED"
    assert order["terminal"] is True
    assert order["filled_quantity"] == 10
    assert order["average_fill_price"] == 101.5
    assert payload["state"]["summary"]["order_count"] == 1
    assert payload["state"]["summary"]["terminal_order_count"] == 1
    assert payload["state"]["summary"]["open_order_count"] == 0


def test_reduce_position_events_to_current_state():
    events = [
        _event(
            "event-1",
            "PAPER_POSITION_OPENED",
            1,
            payload={
                "position_key": "NIFTY26MAY25500CE",
                "symbol": "NIFTY",
                "tradingsymbol": "NIFTY26MAY25500CE",
                "instrument_token": 12345,
                "net_quantity": 10,
                "average_entry_price": 100.0,
                "last_fill_price": 100.0,
            },
        ),
        _event(
            "event-2",
            "PAPER_POSITION_REDUCED",
            2,
            payload={
                "position_key": "NIFTY26MAY25500CE",
                "symbol": "NIFTY",
                "tradingsymbol": "NIFTY26MAY25500CE",
                "instrument_token": 12345,
                "net_quantity": 4,
                "average_entry_price": 100.0,
                "last_fill_price": 110.0,
            },
        ),
    ]

    payload = reduce_paper_events(events).to_dict()
    position = payload["state"]["positions"]["NIFTY26MAY25500CE"]

    assert position["net_quantity"] == 4
    assert position["side"] == "LONG"
    assert position["average_entry_price"] == 100.0
    assert position["last_fill_price"] == 110.0
    assert payload["state"]["summary"]["position_count"] == 1
    assert payload["state"]["summary"]["open_position_count"] == 1


def test_reduce_position_closed_flattens_average_entry():
    events = [
        _event(
            "event-1",
            "PAPER_POSITION_CLOSED",
            1,
            payload={"position_key": "12345", "net_quantity": 0, "average_entry_price": 100.0},
        )
    ]

    payload = reduce_paper_events(events).to_dict()
    position = payload["state"]["positions"]["12345"]

    assert position["net_quantity"] == 0
    assert position["side"] == "FLAT"
    assert position["average_entry_price"] is None
    assert payload["state"]["summary"]["flat_position_count"] == 1


def test_reduce_analytics_events_are_read_only_evidence():
    events = [
        _event("event-1", "PAPER_PNL_MARKED", 1, payload={"unrealized_pnl": 25.0}),
        _event("event-2", "PAPER_SLIPPAGE_MEASURED", 2, payload={"slippage_amount": 3.5}),
        _event("event-3", "PAPER_PERFORMANCE_SNAPSHOT_CREATED", 3, payload={"combined_pnl": 21.5}),
    ]

    payload = reduce_paper_events(events).to_dict()
    state = payload["state"]

    assert state["summary"]["pnl_mark_count"] == 1
    assert state["summary"]["slippage_measurement_count"] == 1
    assert state["summary"]["performance_snapshot_count"] == 1
    assert state["pnl_marks"][0]["read_only"] is True
    assert state["slippage_measurements"][0]["is_order_action"] is False
    assert state["performance_snapshots"][0]["broker_api_called"] is False


def test_reduce_same_input_produces_same_state():
    events = [
        _event("event-1", "PAPER_ORDER_ACCEPTED", 1),
        _event("event-2", "PAPER_ORDER_FILLED", 2, payload={"filled_quantity": 5, "average_fill_price": 99.5}),
    ]

    first = reduce_paper_events(deepcopy(events)).to_dict()
    second = reduce_paper_events(deepcopy(events)).to_dict()

    assert first == second


def test_reducer_blocks_unsafe_event():
    result = reduce_paper_events([_event(is_order_action=True)])
    payload = result.to_dict()

    assert payload["reduced"] is False
    assert payload["status"] == "BLOCKED"
    assert any("PAPER_EVENT_UNSAFE_ORDER_ACTION_FLAG" in blocker for blocker in payload["blockers"])
    assert payload["state"]["summary"]["event_count"] == 0


def test_reducer_blocks_duplicate_event_id():
    event = _event("event-1", "PAPER_ORDER_ACCEPTED", 1)
    duplicate = _event("event-1", "PAPER_ORDER_FILLED", 2, idempotency_key="cycle-1:different")

    payload = reduce_paper_events([event, duplicate]).to_dict()

    assert payload["reduced"] is False
    assert "EVENT_1_PAPER_REDUCER_DUPLICATE_EVENT_ID" in payload["blockers"]


def test_reducer_blocks_duplicate_idempotency_key():
    event = _event("event-1", "PAPER_ORDER_ACCEPTED", 1, idempotency_key="same-key")
    duplicate = _event("event-2", "PAPER_ORDER_FILLED", 2, idempotency_key="same-key")

    payload = reduce_paper_events([event, duplicate]).to_dict()

    assert payload["reduced"] is False
    assert "EVENT_1_PAPER_REDUCER_DUPLICATE_IDEMPOTENCY_KEY" in payload["blockers"]


def test_reducer_blocks_position_event_missing_net_quantity():
    event = _event("event-1", "PAPER_POSITION_OPENED", 1, payload={"position_key": "12345"})

    payload = reduce_paper_events([event]).to_dict()

    assert payload["reduced"] is False
    assert "EVENT_0_PAPER_REDUCER_POSITION_NET_QUANTITY_REQUIRED" in payload["blockers"]


def test_reducer_has_no_order_controls_in_state():
    payload = reduce_paper_events([_event("event-1", "PAPER_ORDER_ACCEPTED", 1)]).to_dict()
    serialized = str(payload).lower()

    assert "submit_order" not in serialized
    assert "modify_order" not in serialized
    assert "cancel_order" not in serialized
    assert "exit_order" not in serialized
    assert "place_order" not in serialized

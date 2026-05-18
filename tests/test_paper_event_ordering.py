from __future__ import annotations

from paper_trading.event_ordering import (
    guard_paper_event_ordering,
    paper_event_ordering_guard_schema_contract,
)


def _event(event_id="event-1", sequence=1, cycle_id="cycle-1", ts_epoch=100.0, **overrides):
    payload = {
        "schema_version": "1.0",
        "event_id": event_id,
        "cycle_id": cycle_id,
        "event_sequence": sequence,
        "candidate_id": "candidate-1",
        "strategy_id": "orb_retest",
        "paper_order_intent_id": "intent-1",
        "paper_order_id": "order-1",
        "event_type": "PAPER_ORDER_ACCEPTED",
        "ts_epoch": ts_epoch,
        "idempotency_key": f"{cycle_id}:{event_id}",
        "payload": {"source": "test"},
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def test_paper_event_ordering_schema_contract_is_safe():
    contract = paper_event_ordering_guard_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["guard_type"] == "PAPER_EVENT_ORDERING_IDEMPOTENCY_GUARD"
    assert contract["consumes"] == ["CANONICAL_PAPER_EVENT_JOURNAL"]
    assert contract["ordering_rules"]["repair_or_sort_events"] is False
    assert contract["safe_flags"] == {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert "ordered_events" in contract["required_result_keys"]
    assert "cycles" in contract["required_result_keys"]


def test_guard_accepts_strictly_contiguous_cycle_events():
    events = [
        _event("event-1", sequence=1, ts_epoch=100.0),
        _event("event-2", sequence=2, ts_epoch=100.0),
        _event("event-3", sequence=3, ts_epoch=101.5),
    ]

    payload = guard_paper_event_ordering(events).to_dict()

    assert payload["valid"] is True
    assert payload["status"] == "VALID"
    assert payload["event_count"] == 3
    assert [event["event_id"] for event in payload["ordered_events"]] == ["event-1", "event-2", "event-3"]
    assert payload["cycles"]["cycle-1"]["event_count"] == 3
    assert payload["cycles"]["cycle-1"]["first_sequence"] == 1
    assert payload["cycles"]["cycle-1"]["last_sequence"] == 3
    assert payload["paper_only"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_guard_accepts_independent_cycles_that_each_start_at_one():
    events = [
        _event("event-1", sequence=1, cycle_id="cycle-a", ts_epoch=100.0),
        _event("event-2", sequence=1, cycle_id="cycle-b", ts_epoch=90.0),
        _event("event-3", sequence=2, cycle_id="cycle-a", ts_epoch=101.0),
        _event("event-4", sequence=2, cycle_id="cycle-b", ts_epoch=91.0),
    ]

    payload = guard_paper_event_ordering(events).to_dict()

    assert payload["valid"] is True
    assert payload["cycles"]["cycle-a"]["event_count"] == 2
    assert payload["cycles"]["cycle-b"]["event_count"] == 2
    assert payload["cycles"]["cycle-a"]["last_sequence"] == 2
    assert payload["cycles"]["cycle-b"]["last_sequence"] == 2


def test_guard_empty_event_list_is_safe_empty():
    payload = guard_paper_event_ordering([]).to_dict()

    assert payload["valid"] is True
    assert payload["status"] == "EMPTY"
    assert payload["event_count"] == 0
    assert payload["warnings"] == ["PAPER_EVENT_ORDERING_EMPTY_EVENT_LIST"]
    assert payload["paper_only"] is True
    assert payload["read_only"] is True


def test_guard_blocks_missing_events():
    payload = guard_paper_event_ordering(None).to_dict()

    assert payload["valid"] is False
    assert payload["status"] == "BLOCKED"
    assert payload["blockers"] == ["PAPER_EVENT_ORDERING_EVENTS_REQUIRED"]


def test_guard_blocks_non_list_events():
    payload = guard_paper_event_ordering({"not": "a-list"}).to_dict()  # type: ignore[arg-type]

    assert payload["valid"] is False
    assert payload["blockers"] == ["PAPER_EVENT_ORDERING_EVENTS_MUST_BE_LIST"]


def test_guard_blocks_duplicate_event_id():
    events = [
        _event("event-1", sequence=1),
        _event("event-1", sequence=2, idempotency_key="cycle-1:different"),
    ]

    payload = guard_paper_event_ordering(events).to_dict()

    assert payload["valid"] is False
    assert "EVENT_1_PAPER_EVENT_ORDERING_DUPLICATE_EVENT_ID" in payload["blockers"]
    assert payload["ordered_events"] == []


def test_guard_blocks_duplicate_idempotency_key():
    events = [
        _event("event-1", sequence=1, idempotency_key="same-key"),
        _event("event-2", sequence=2, idempotency_key="same-key"),
    ]

    payload = guard_paper_event_ordering(events).to_dict()

    assert payload["valid"] is False
    assert "EVENT_1_PAPER_EVENT_ORDERING_DUPLICATE_IDEMPOTENCY_KEY" in payload["blockers"]


def test_guard_blocks_sequence_gap():
    events = [
        _event("event-1", sequence=1),
        _event("event-2", sequence=3),
    ]

    payload = guard_paper_event_ordering(events).to_dict()

    assert payload["valid"] is False
    assert "EVENT_1_PAPER_EVENT_SEQUENCE_GAP_OR_REGRESSION:cycle-1:1->3" in payload["blockers"]


def test_guard_blocks_sequence_regression():
    events = [
        _event("event-1", sequence=1),
        _event("event-2", sequence=2),
        _event("event-3", sequence=1),
    ]

    payload = guard_paper_event_ordering(events).to_dict()

    assert payload["valid"] is False
    assert "EVENT_2_PAPER_EVENT_SEQUENCE_GAP_OR_REGRESSION:cycle-1:2->1" in payload["blockers"]


def test_guard_blocks_cycle_starting_above_one():
    payload = guard_paper_event_ordering([_event("event-1", sequence=2)]).to_dict()

    assert payload["valid"] is False
    assert "EVENT_0_PAPER_EVENT_SEQUENCE_MUST_START_AT_1:cycle-1:2" in payload["blockers"]


def test_guard_blocks_timestamp_regression_inside_cycle():
    events = [
        _event("event-1", sequence=1, ts_epoch=100.0),
        _event("event-2", sequence=2, ts_epoch=99.99),
    ]

    payload = guard_paper_event_ordering(events).to_dict()

    assert payload["valid"] is False
    assert "EVENT_1_PAPER_EVENT_TS_EPOCH_REGRESSION:cycle-1:100.0->99.99" in payload["blockers"]


def test_guard_blocks_unsafe_canonical_event_flags():
    payload = guard_paper_event_ordering([_event("event-1", sequence=1, broker_api_called=True)]).to_dict()

    assert payload["valid"] is False
    assert any("PAPER_EVENT_UNSAFE_BROKER_API_FLAG" in blocker for blocker in payload["blockers"])
    assert payload["ordered_events"] == []


def test_guard_does_not_silently_sort_or_repair_input_order():
    events = [
        _event("event-2", sequence=2, ts_epoch=101.0),
        _event("event-1", sequence=1, ts_epoch=100.0),
    ]

    payload = guard_paper_event_ordering(events).to_dict()

    assert payload["valid"] is False
    assert "EVENT_0_PAPER_EVENT_SEQUENCE_MUST_START_AT_1:cycle-1:2" in payload["blockers"]
    assert "EVENT_1_PAPER_EVENT_SEQUENCE_GAP_OR_REGRESSION:cycle-1:2->1" in payload["blockers"]

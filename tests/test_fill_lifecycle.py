from __future__ import annotations

from fill_lifecycle import FillLifecycleStatus, normalize_fill_lifecycle


def test_fill_lifecycle_tracks_filled_state():
    state = normalize_fill_lifecycle(
        [
            {"candidate_id": "c1", "status": "ORDER_INTENT_CREATED", "ts_epoch": 1, "quantity": 50},
            {"candidate_id": "c1", "status": "ORDER_SUBMITTED", "ts_epoch": 2, "order_id": "local-1"},
            {"candidate_id": "c1", "status": "ORDER_ACCEPTED", "ts_epoch": 3, "broker_order_id": "b-1"},
            {"candidate_id": "c1", "status": "PARTIALLY_FILLED", "ts_epoch": 4, "filled_quantity": 20, "average_price": 101.5},
            {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 5, "filled_quantity": 50, "average_price": 102.0},
        ]
    )

    assert state.candidate_id == "c1"
    assert state.current_status == FillLifecycleStatus.FILLED
    assert state.terminal is False
    assert state.filled_quantity == 50
    assert state.average_price == 102.0
    assert [event.status for event in state.events] == [
        FillLifecycleStatus.ORDER_INTENT_CREATED,
        FillLifecycleStatus.ORDER_SUBMITTED,
        FillLifecycleStatus.ORDER_ACCEPTED,
        FillLifecycleStatus.PARTIALLY_FILLED,
        FillLifecycleStatus.FILLED,
    ]
    assert state.to_dict()["is_order_submission"] is False


def test_fill_lifecycle_tracks_position_closed_terminal_state():
    state = normalize_fill_lifecycle(
        [
            {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 1, "filled_qty": 50, "avg_price": 100},
            {"candidate_id": "c1", "status": "EXIT_SUBMITTED", "ts_epoch": 2},
            {"candidate_id": "c1", "status": "EXIT_FILLED", "ts_epoch": 3, "filled_qty": 50, "avg_price": 105},
            {"candidate_id": "c1", "status": "POSITION_CLOSED", "ts_epoch": 4},
        ]
    )

    assert state.current_status == FillLifecycleStatus.POSITION_CLOSED
    assert state.terminal is True
    assert state.filled_quantity == 50
    assert state.average_price == 105


def test_fill_lifecycle_maps_common_status_aliases():
    state = normalize_fill_lifecycle(
        [
            {"candidate_id": "c1", "order_status": "OPEN", "ts_epoch": 1},
            {"candidate_id": "c1", "order_status": "COMPLETE", "ts_epoch": 2, "filled": 25},
        ]
    )

    assert [event.status for event in state.events] == [
        FillLifecycleStatus.ORDER_ACCEPTED,
        FillLifecycleStatus.FILLED,
    ]
    assert state.current_status == FillLifecycleStatus.FILLED
    assert state.filled_quantity == 25


def test_fill_lifecycle_rejected_is_terminal():
    state = normalize_fill_lifecycle(
        [
            {"candidate_id": "c1", "status": "ORDER_SUBMITTED", "ts_epoch": 1},
            {"candidate_id": "c1", "status": "REJECTED", "ts_epoch": 2, "rejection_reason": "RMS blocked"},
        ]
    )

    assert state.current_status == FillLifecycleStatus.ORDER_REJECTED
    assert state.terminal is True
    assert state.events[-1].reason == "RMS blocked"


def test_fill_lifecycle_empty_state_is_blocked_unknown():
    state = normalize_fill_lifecycle([], candidate_id="c1")

    assert state.candidate_id == "c1"
    assert state.current_status == FillLifecycleStatus.UNKNOWN
    assert state.events == []
    assert state.blockers == ["NO_FILL_LIFECYCLE_EVENTS"]
    assert state.terminal is False


def test_fill_lifecycle_filters_candidate_id():
    state = normalize_fill_lifecycle(
        [
            {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 2},
            {"candidate_id": "c2", "status": "REJECTED", "ts_epoch": 3},
        ],
        candidate_id="c1",
    )

    assert state.candidate_id == "c1"
    assert len(state.events) == 1
    assert state.current_status == FillLifecycleStatus.FILLED


def test_fill_lifecycle_unknown_status_adds_warning_and_blocker_if_latest():
    state = normalize_fill_lifecycle(
        [
            {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 1},
            {"candidate_id": "c1", "status": "BROKER_WEIRD_STATE", "ts_epoch": 2},
        ]
    )

    assert state.current_status == FillLifecycleStatus.UNKNOWN
    assert state.blockers == ["UNKNOWN_FILL_LIFECYCLE_STATUS"]
    assert "UNKNOWN_STATUS_EVENT_PRESENT" in state.warnings

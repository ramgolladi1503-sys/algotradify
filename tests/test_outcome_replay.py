from __future__ import annotations

from outcome_replay import OutcomeStatus, normalize_outcome_replay


def test_outcome_replay_tracks_selected_to_filled_timeline():
    summary = normalize_outcome_replay(
        [
            {"candidate_id": "c1", "status": "SELECTED", "ts_epoch": 1, "quality_score": 86, "selection_reason": "highest_quality_score"},
            {"candidate_id": "c1", "status": "ORDER_SUBMITTED", "ts_epoch": 2},
            {"candidate_id": "c1", "status": "ORDER_ACCEPTED", "ts_epoch": 3},
            {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 4, "quality_score": 88},
        ]
    )

    assert summary.candidate_id == "c1"
    assert summary.current_status == OutcomeStatus.FILLED
    assert summary.terminal is True
    assert summary.selected_count == 1
    assert summary.filled_count == 1
    assert summary.rejected_count == 0
    assert summary.best_quality_score == 88
    assert [event.status for event in summary.events] == [
        OutcomeStatus.SELECTED,
        OutcomeStatus.SUBMITTED,
        OutcomeStatus.ACCEPTED,
        OutcomeStatus.FILLED,
    ]
    assert summary.to_dict()["is_order_action"] is False
    assert summary.events[0].is_order_action is False


def test_outcome_replay_tracks_blocked_candidate():
    summary = normalize_outcome_replay(
        [
            {"candidate_id": "c1", "status": "BLOCKED", "ts_epoch": 1, "reason": "MISSING_RISK_READINESS"},
        ]
    )

    assert summary.current_status == OutcomeStatus.BLOCKED
    assert summary.terminal is False
    assert summary.blocked_count == 1
    assert summary.events[0].reason == "MISSING_RISK_READINESS"


def test_outcome_replay_tracks_rejected_terminal_state():
    summary = normalize_outcome_replay(
        [
            {"candidate_id": "c1", "status": "SELECTED", "ts_epoch": 1},
            {"candidate_id": "c1", "status": "REJECTED", "ts_epoch": 2, "rejection_reason": "RMS blocked"},
        ]
    )

    assert summary.current_status == OutcomeStatus.REJECTED
    assert summary.terminal is True
    assert summary.rejected_count == 1
    assert summary.events[-1].reason == "RMS blocked"


def test_outcome_replay_maps_common_aliases():
    summary = normalize_outcome_replay(
        [
            {"candidate_id": "c1", "status": "OPEN", "ts_epoch": 1},
            {"candidate_id": "c1", "status": "COMPLETE", "ts_epoch": 2},
            {"candidate_id": "c1", "status": "POSITION_CLOSED", "ts_epoch": 3},
        ]
    )

    assert [event.status for event in summary.events] == [
        OutcomeStatus.ACCEPTED,
        OutcomeStatus.FILLED,
        OutcomeStatus.CLOSED,
    ]
    assert summary.current_status == OutcomeStatus.CLOSED
    assert summary.terminal is True


def test_outcome_replay_empty_state():
    summary = normalize_outcome_replay([], candidate_id="c1")

    assert summary.candidate_id == "c1"
    assert summary.current_status == OutcomeStatus.UNKNOWN
    assert summary.blockers == ["NO_OUTCOME_EVENTS"]
    assert summary.events == []
    assert summary.is_order_action is False


def test_outcome_replay_filters_candidate_id():
    summary = normalize_outcome_replay(
        [
            {"candidate_id": "c1", "status": "FILLED", "ts_epoch": 1},
            {"candidate_id": "c2", "status": "REJECTED", "ts_epoch": 2},
        ],
        candidate_id="c2",
    )

    assert summary.candidate_id == "c2"
    assert len(summary.events) == 1
    assert summary.current_status == OutcomeStatus.REJECTED


def test_outcome_replay_unknown_status_is_visible():
    summary = normalize_outcome_replay(
        [
            {"candidate_id": "c1", "status": "BROKER_WEIRD", "ts_epoch": 1},
        ]
    )

    assert summary.current_status == OutcomeStatus.UNKNOWN
    assert summary.blockers == ["UNKNOWN_OUTCOME_STATUS"]
    assert "UNKNOWN_OUTCOME_EVENT_PRESENT" in summary.warnings

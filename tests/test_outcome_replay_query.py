from __future__ import annotations

from outcome_replay import filter_outcome_replay_records, replay_query_metadata


_RECORDS = [
    {"candidate_id": "c1", "status": "SELECTED", "strategy": "orb_retest", "ts_epoch": 10, "quality_score": 80},
    {"candidate_id": "c1", "status": "FILLED", "strategy": "orb_retest", "ts_epoch": 20, "quality_score": 90},
    {"candidate_id": "c2", "status": "REJECTED", "strategy": "vwap_pullback", "ts_epoch": 30},
    {"candidate_id": "c3", "status": "BLOCKED", "evidence": {"strategy_family": "zero_hero"}, "ts_epoch": 40},
]


def test_filter_outcome_replay_records_by_candidate_id():
    rows = filter_outcome_replay_records(_RECORDS, candidate_id="c1")

    assert [row["candidate_id"] for row in rows] == ["c1", "c1"]


def test_filter_outcome_replay_records_by_single_status():
    rows = filter_outcome_replay_records(_RECORDS, status="filled")

    assert len(rows) == 1
    assert rows[0]["status"] == "FILLED"


def test_filter_outcome_replay_records_by_multiple_statuses():
    rows = filter_outcome_replay_records(_RECORDS, status="filled,rejected")

    assert [row["status"] for row in rows] == ["FILLED", "REJECTED"]


def test_filter_outcome_replay_records_by_strategy_from_top_level_or_evidence():
    direct = filter_outcome_replay_records(_RECORDS, strategy="orb_retest")
    nested = filter_outcome_replay_records(_RECORDS, strategy="zero_hero")

    assert [row["candidate_id"] for row in direct] == ["c1", "c1"]
    assert [row["candidate_id"] for row in nested] == ["c3"]


def test_filter_outcome_replay_records_by_inclusive_time_window():
    rows = filter_outcome_replay_records(_RECORDS, ts_from_epoch=20, ts_to_epoch=30)

    assert [row["candidate_id"] for row in rows] == ["c1", "c2"]


def test_filter_outcome_replay_records_combines_filters():
    rows = filter_outcome_replay_records(
        _RECORDS,
        candidate_id="c1",
        status="filled",
        strategy="orb_retest",
        ts_from_epoch=15,
        ts_to_epoch=25,
    )

    assert len(rows) == 1
    assert rows[0]["status"] == "FILLED"


def test_replay_query_metadata_is_read_only():
    metadata = replay_query_metadata(
        candidate_id="c1",
        status="filled",
        strategy="orb_retest",
        ts_from_epoch=1,
        ts_to_epoch=2,
        source_count=10,
        result_count=1,
    )

    assert metadata == {
        "candidate_id": "c1",
        "status": "filled",
        "strategy": "orb_retest",
        "ts_from_epoch": 1,
        "ts_to_epoch": 2,
        "source_count": 10,
        "result_count": 1,
        "read_only": True,
        "is_order_action": False,
    }

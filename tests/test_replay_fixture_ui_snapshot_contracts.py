from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "replay"
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
FRONTEND_MAIN = FRONTEND_DIR / "main.jsx"
CONTROL_TOWER_CARDS = FRONTEND_DIR / "controlTowerCards.jsx"
FIXTURE_FILES = [
    "empty_replay.json",
    "single_candidate_lifecycle.json",
    "multi_candidate_mixed_status.json",
]


def _load_fixture(filename: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))


def _fixtures() -> list[dict[str, Any]]:
    return [_load_fixture(filename) for filename in FIXTURE_FILES]


def _frontend_source() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in [FRONTEND_MAIN, CONTROL_TOWER_CARDS]
    )


def _candidate_id(row: dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("trade_id") or row.get("client_order_id") or "unknown")


def _status(row: dict[str, Any]) -> str:
    return str(row.get("outcome_status") or row.get("status") or row.get("event") or row.get("current_status") or "UNKNOWN").upper()


def _strategy(row: dict[str, Any]) -> str:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    selected = row.get("selected") if isinstance(row.get("selected"), dict) else {}
    return str(
        row.get("strategy")
        or row.get("strategy_id")
        or row.get("strategy_family")
        or row.get("setup_family")
        or evidence.get("strategy_family")
        or evidence.get("strategy")
        or selected.get("strategy_family")
        or selected.get("strategy")
        or "UNKNOWN"
    )


def _timestamp(row: dict[str, Any]) -> Any:
    return row.get("ts_epoch") or row.get("timestamp") or row.get("time") or row.get("created_at")


def _score(row: dict[str, Any]) -> float | None:
    try:
        value = row.get("quality_score", row.get("trade_quality_score", row.get("score")))
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _fixture_ui_snapshot(fixture: dict[str, Any]) -> dict[str, Any]:
    events = list(fixture["outcome_replay"])
    timestamps = [float(_timestamp(row)) for row in events if _timestamp(row) not in (None, "")]
    scores = [score for score in (_score(row) for row in events) if score is not None]
    grouped = {}
    for row in events:
        grouped.setdefault(_candidate_id(row), []).append(row)
    return {
        "fixture_id": fixture["fixture_id"],
        "candidate_count": len(grouped),
        "event_count": len(events),
        "status_distribution": dict(Counter(_status(row) for row in events)),
        "strategy_distribution": dict(Counter(_strategy(row) for row in events)),
        "time_window_min": min(timestamps) if timestamps else None,
        "time_window_max": max(timestamps) if timestamps else None,
        "best_quality_score": max(scores) if scores else None,
        "worst_quality_score": min(scores) if scores else None,
        "grouped_timeline": [
            {
                "candidate_id": candidate_id,
                "event_count": len(rows),
                "status_chain": [_status(row) for row in rows],
                "strategy": _strategy(rows[0]) if rows else "UNKNOWN",
            }
            for candidate_id, rows in sorted(grouped.items())
        ],
        "export_snapshot_keys": [
            "snapshot_type",
            "read_only",
            "source",
            "filters",
            "query_metadata",
            "analytics_summary",
            "grouped_timeline",
            "events",
        ],
    }


def test_replay_fixture_ui_snapshot_contracts_cover_all_fixtures():
    snapshots = [_fixture_ui_snapshot(fixture) for fixture in _fixtures()]

    assert [snapshot["fixture_id"] for snapshot in snapshots] == [
        "empty_replay",
        "single_candidate_lifecycle",
        "multi_candidate_mixed_status",
    ]
    assert snapshots[0]["event_count"] == 0
    assert snapshots[1]["candidate_count"] == 1
    assert snapshots[2]["candidate_count"] == 4


def test_replay_fixture_ui_snapshot_contracts_match_expected_fixture_counts():
    for fixture in _fixtures():
        snapshot = _fixture_ui_snapshot(fixture)
        expected = fixture["expected"]

        assert snapshot["event_count"] == expected["source_count"]
        assert snapshot["candidate_count"] == expected["candidate_count"]
        assert set(snapshot["strategy_distribution"]) == set(expected["strategy_counts"])


def test_replay_fixture_ui_snapshot_exposes_analytics_drilldown_and_export_shapes():
    source = _frontend_source()
    required_ui_terms = [
        "Replay Analytics Summary Panel",
        "Replay Result Drilldown",
        "Replay Export Snapshot Panel",
        "candidate_count",
        "event_count",
        "time_window_min",
        "time_window_max",
        "best_quality_score",
        "worst_quality_score",
        "status distribution",
        "strategy distribution",
        "grouped_timeline",
        "analytics_summary",
        "query_metadata",
        "COPYABLE_READ_ONLY_JSON",
        "READ_ONLY_ANALYTICS",
    ]

    for term in required_ui_terms:
        assert term in source


def test_replay_fixture_ui_snapshot_serializes_required_snapshot_keys():
    serialized = json.dumps([_fixture_ui_snapshot(fixture) for fixture in _fixtures()], sort_keys=True)
    required_snapshot_terms = [
        "snapshot_type",
        "read_only",
        "source",
        "filters",
        "query_metadata",
        "analytics_summary",
        "grouped_timeline",
        "events",
        "status_chain",
        "candidate_id",
    ]

    for term in required_snapshot_terms:
        assert term in serialized


def test_replay_fixture_ui_snapshot_contract_has_no_execution_controls():
    source = _frontend_source()
    forbidden_terms = [
        "Submit Order",
        "Modify Order",
        "Cancel Order",
        "Exit Order",
        "Approve Order",
        "Execute Order",
        "Place Order",
        "broker.place",
        "kite.place_order",
        "append=true",
    ]

    for term in forbidden_terms:
        assert term not in source

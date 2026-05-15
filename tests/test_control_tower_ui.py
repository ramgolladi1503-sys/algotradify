from __future__ import annotations

from pathlib import Path


FRONTEND_MAIN = Path(__file__).resolve().parents[1] / "frontend" / "main.jsx"


def _frontend_source() -> str:
    return FRONTEND_MAIN.read_text(encoding="utf-8")


def test_control_tower_ui_calls_all_tradability_endpoints():
    source = _frontend_source()

    required_endpoints = [
        "/runtime/health",
        "/runtime/preflight",
        "/runtime/snapshot",
        "/opportunities?limit=20",
        "/candidate-truth?limit=20",
        "/opportunity-layer?limit=20",
        "/execution-readiness?limit=20",
        "/trade-quality?limit=20",
        "/top-executable?limit=20",
        "/fill-lifecycle",
        "/outcome-replay",
    ]

    for endpoint in required_endpoints:
        assert endpoint in source


def test_control_tower_ui_renders_required_sections():
    source = _frontend_source()

    required_sections = [
        "Algotradify Control Tower",
        "Frontend Filters",
        "Runtime",
        "Cycle Snapshot",
        "Tradability Summary",
        "Top Executable",
        "Readiness Breakdown Chart",
        "Outcome Counts Chart",
        "Quality Score Distribution Chart",
        "Candidate Truth Breakdown Chart",
        "Outcome Replay Drilldown",
        "Execution Readiness",
        "Trade Quality",
        "Candidate Truth",
        "Opportunity Layer",
        "Fill Lifecycle",
        "Raw Runtime Opportunities",
        "Live Event Feed",
    ]

    for section in required_sections:
        assert section in source


def test_control_tower_ui_exposes_blockers_and_no_order_boundaries():
    source = _frontend_source()

    assert "blockers" in source
    assert "execution_allowed" in source
    assert "quality_score" in source
    assert "selector_rejection_reasons" in source
    assert "is_order" in source
    assert "is_order_submission" in source
    assert "is_order_action" in source


def test_control_tower_ui_exposes_outcome_replay_filter_counts_and_timeline():
    source = _frontend_source()

    assert "replayCandidateId" in source
    assert "candidate_id filter" in source
    assert "Replay" in source
    assert "selected_count" in source
    assert "blocked_count" in source
    assert "filled_count" in source
    assert "rejected_count" in source
    assert "best_quality_score" in source
    assert "outcome blockers" in source
    assert "no outcome replay events yet" in source


def test_control_tower_ui_exposes_frontend_filters_and_analytics():
    source = _frontend_source()

    required_filter_terms = [
        "candidate search/filter",
        "status filter",
        "blocked-only view",
        "selected-only view",
        "allowed-only view",
        "rejected-only view",
        "quality score threshold filter",
        "Reset filters",
        "applyFilters",
        "BarChart",
    ]

    for term in required_filter_terms:
        assert term in source

    required_analytics_terms = [
        "readinessBreakdown",
        "qualityDistribution",
        "outcomeCounts",
        "truthBreakdown",
    ]

    for term in required_analytics_terms:
        assert term in source


def test_control_tower_ui_keeps_websocket_event_feed():
    source = _frontend_source()

    assert "new WebSocket(WS_URL)" in source
    assert "runtime_snapshot" in source
    assert "raw_ws" in source

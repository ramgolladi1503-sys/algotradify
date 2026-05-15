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
    ]

    for endpoint in required_endpoints:
        assert endpoint in source


def test_control_tower_ui_renders_required_sections():
    source = _frontend_source()

    required_sections = [
        "Algotradify Control Tower",
        "Runtime",
        "Cycle Snapshot",
        "Tradability Summary",
        "Top Executable",
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


def test_control_tower_ui_keeps_websocket_event_feed():
    source = _frontend_source()

    assert "new WebSocket(WS_URL)" in source
    assert "runtime_snapshot" in source
    assert "raw_ws" in source

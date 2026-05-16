from __future__ import annotations

from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
FRONTEND_MAIN = FRONTEND_DIR / "main.jsx"
CONTROL_TOWER_CARDS = FRONTEND_DIR / "controlTowerCards.jsx"


def _frontend_source() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in [FRONTEND_MAIN, CONTROL_TOWER_CARDS]
    )


def _frontend_main_source() -> str:
    return FRONTEND_MAIN.read_text(encoding="utf-8")


def _cards_source() -> str:
    return CONTROL_TOWER_CARDS.read_text(encoding="utf-8")


def test_control_tower_ui_component_split_exists():
    main_source = _frontend_main_source()
    cards_source = _cards_source()

    required_component_exports = [
        "ExecutionSafetyCard",
        "DryRunExecutionAdapterCard",
        "DryRunEvidenceExportPreviewCard",
        "OutcomeReplayDrilldownCard",
        "BarChart",
        "Table",
    ]

    assert "from './controlTowerCards.jsx'" in main_source
    for component in required_component_exports:
        assert component in main_source
        assert f"function {component}" in cards_source or f"export function {component}" in cards_source


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
        "/execution-safety?limit=20",
        "/dry-run-execution?limit=20",
        "/dry-run-execution/export?limit=20",
        "/fill-lifecycle",
        "/outcome-replay",
    ]

    for endpoint in required_endpoints:
        assert endpoint in source


def test_control_tower_ui_renders_required_sections():
    source = _frontend_source()

    required_sections = [
        "Algotradify Control Tower",
        "Operator Views",
        "Frontend Filters",
        "Runtime",
        "Cycle Snapshot",
        "Tradability Summary",
        "Top Executable",
        "Execution Safety",
        "Dry-Run Execution Adapter",
        "Dry-Run Evidence Export Preview",
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
    assert "warnings" in source
    assert "execution_allowed" in source
    assert "execution_permitted" in source
    assert "quality_score" in source
    assert "selector_rejection_reasons" in source
    assert "is_order" in source
    assert "is_order_submission" in source
    assert "is_order_action" in source
    assert "safety_visibility_only" in source


def test_control_tower_ui_exposes_execution_safety_decision():
    source = _frontend_source()

    required_terms = [
        "executionSafety",
        "safety blockers",
        "safety warnings",
        "requires_manual_approval",
        "readiness_records_checked",
        "execution_permitted",
        "safety_visibility_only",
    ]

    for term in required_terms:
        assert term in source


def test_control_tower_ui_exposes_dry_run_execution_visibility_without_append():
    source = _frontend_source()

    required_terms = [
        "dryRunExecution",
        "Dry-Run Execution Adapter",
        "dry_run_only",
        "dry_run_order_id",
        "real_order_id",
        "broker_api_called",
        "dry-run blockers",
        "dry-run warnings",
        "Preview Dry Run",
    ]

    for term in required_terms:
        assert term in source

    assert "/dry-run-execution?limit=20" in source
    assert "append=true" not in source


def test_control_tower_ui_exposes_export_preview_without_order_controls():
    source = _frontend_source()

    required_terms = [
        "dryRunExport",
        "Dry-Run Evidence Export Preview",
        "/dry-run-execution/export?limit=20",
        "bundle_type",
        "status",
        "candidate_id",
        "dry_run_order_id",
        "dry_run_only",
        "is_order_action",
        "broker_api_called",
        "real_order_id",
        "export_preview_only",
        "blockers",
        "warnings",
        "selected snapshot",
        "safety snapshot",
        "approval snapshot",
        "readiness snapshot",
        "exportFlagWarnings",
        "UNSAFE_FLAG_WARNING",
    ]

    for term in required_terms:
        assert term in source

    forbidden_controls = [
        "Submit Order",
        "Modify Order",
        "Cancel Order",
        "Exit Order",
        "Approve Order",
        "Execute Order",
        "Place Order",
    ]
    for control in forbidden_controls:
        assert control not in source

    assert "append=true" not in source


def test_control_tower_export_preview_ux_hardening():
    source = _frontend_source()

    required_terms = [
        "exportPreviewStatus",
        "FlagCheckMetric",
        "ExportBundleState",
        "ExportFlagChecks",
        "Expected safe flags",
        "safe expected flag",
        "unsafe flag mismatch",
        "Why this bundle is safe",
        "No export bundle returned yet",
        "Export bundle blocked",
        "Snapshot drilldowns",
        "SAFE_EXPORT_FLAGS",
        "EXPORT_BUNDLE_BLOCKED",
        "NO_EXPORT_BUNDLE",
        "This card stays read-only and exposes no order controls",
        "This bundle is safe because dry_run_only is true",
    ]

    for term in required_terms:
        assert term in source

    assert "append=true" not in source


def test_control_tower_ui_exposes_dry_run_evidence_drilldown_and_operator_explanation():
    source = _frontend_source()

    required_terms = [
        "dryRunExplanation",
        "Dry-run operator explanation",
        "selected candidate snapshot",
        "execution safety snapshot",
        "approval snapshot",
        "readiness snapshot",
        "outcome event",
        "selectedCandidateSnapshot",
        "executionSafetySnapshot",
        "approvalSnapshot",
        "readinessSnapshot",
        "outcomeEvent",
        "JsonBlock",
        "local simulation evidence only",
        "Resolve the upstream evidence before moving forward",
    ]

    for term in required_terms:
        assert term in source


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


def test_control_tower_ui_persists_preferences_and_operator_views():
    source = _frontend_source()

    required_terms = [
        "PERSISTED_PREFS_KEY",
        "localStorage",
        "loadPersistedPreferences",
        "savePersistedPreferences",
        "clearPersistedPreferences",
        "OPERATOR_VIEWS",
        "Default view",
        "Blocked focus",
        "Trade-ready focus",
        "Replay focus",
        "Lifecycle focus",
        "Reset to default view",
        "Persisted UI Preferences",
        "operatorView",
        "setOperatorView",
        "resetToDefaultView",
    ]

    for term in required_terms:
        assert term in source


def test_control_tower_ui_keeps_websocket_event_feed():
    source = _frontend_source()

    assert "new WebSocket(WS_URL)" in source
    assert "runtime_snapshot" in source
    assert "raw_ws" in source

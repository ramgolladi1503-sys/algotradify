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
        "EvidenceHealthPanel",
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
        "/evidence-health?limit=20",
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
        "Evidence Health Panel",
        "Readiness Breakdown Chart",
        "Outcome Counts Chart",
        "Quality Score Distribution Chart",
        "Candidate Truth Breakdown Chart",
        "Replay Timeline UI",
        "Replay Result Drilldown",
        "Replay Analytics Summary Panel",
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


def test_control_tower_ui_exposes_evidence_health_panel_without_order_controls():
    source = _frontend_source()

    required_terms = [
        "evidenceHealth",
        "Evidence Health Panel",
        "/evidence-health?limit=20",
        "evidence_health_only",
        "schema_count",
        "valid_count",
        "invalid_count",
        "missing_key_count",
        "safe_flag_violation_count",
        "warning_count",
        "missing_keys",
        "safe_flag_violations",
        "No evidence health returned yet",
        "read-only integrity results",
        "This panel validates evidence shape and safe flags only",
        "it exposes no execution controls",
    ]

    for term in required_terms:
        assert term in source

    assert "append=true" not in source
    for forbidden in ["Submit Order", "Modify Order", "Cancel Order", "Exit Order", "Approve Order", "Execute Order", "Place Order"]:
        assert forbidden not in source


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

    required_terms = [
        "replayQuery",
        "DEFAULT_REPLAY_QUERY",
        "candidate_id filter",
        "status filter",
        "strategy filter",
        "ts_from_epoch time range filter",
        "ts_to_epoch time range filter",
        "Apply replay query filters",
        "Reset replay query filters",
        "selected_count",
        "blocked_count",
        "filled_count",
        "rejected_count",
        "best_quality_score",
        "outcome blockers",
        "Replay timeline events",
        "no outcome replay events yet",
    ]

    for term in required_terms:
        assert term in source


def test_control_tower_replay_timeline_ui_builds_backend_query_contract():
    source = _frontend_source()

    required_terms = [
        "buildReplayQueryString",
        "new URLSearchParams",
        "candidate_id",
        "status",
        "strategy",
        "ts_from_epoch",
        "ts_to_epoch",
        "replayQueryString",
        "`/outcome-replay${replayQueryString}`",
    ]

    for term in required_terms:
        assert term in source

    assert "replayCandidateId" not in source
    assert "append=true" not in source


def test_control_tower_replay_timeline_ui_exposes_query_metadata_and_safe_flags():
    source = _frontend_source()

    required_terms = [
        "ReplayTimelineMetadata",
        "replayQueryMetadata",
        "Replay query metadata",
        "source_count",
        "result_count",
        "read_only",
        "is_order_action",
        "Replay query is read-only and is_order_action=false",
        "Replay metadata is outside the safe read boundary.",
        "READ_ONLY_REPLAY_TIMELINE",
    ]

    for term in required_terms:
        assert term in source

    for forbidden in ["Submit Order", "Modify Order", "Cancel Order", "Exit Order", "Approve Order", "Execute Order", "Place Order", "broker.place", "kite.place_order"]:
        assert forbidden not in source


def test_control_tower_replay_result_drilldown_groups_events_and_status_chain():
    source = _frontend_source()

    required_terms = [
        "Replay Result Drilldown",
        "ReplayResultDrilldown",
        "ReplayResultDrilldownGroup",
        "groupReplayEventsByCandidate",
        "replayTimelineEvents",
        "replayStatusTransitionChain",
        "Grouped by candidate_id",
        "ordered by timestamp",
        "status transition chain",
        "timeline order",
        "event_count",
        "first_timestamp",
        "last_timestamp",
        "event evidence",
    ]

    for term in required_terms:
        assert term in source


def test_control_tower_replay_result_drilldown_shows_fields_and_empty_state():
    source = _frontend_source()

    required_terms = [
        "replayEventCandidateId",
        "replayEventStatus",
        "replayEventStrategy",
        "replayEventTimestamp",
        "No replay results match the active filters",
        "Check candidate_id, status, strategy, and time range filters",
        "active replay filters",
        "ReplayEmptyState",
    ]

    for term in required_terms:
        assert term in source

    assert "append=true" not in source
    for forbidden in ["Submit Order", "Modify Order", "Cancel Order", "Exit Order", "Approve Order", "Execute Order", "Place Order"]:
        assert forbidden not in source


def test_control_tower_replay_analytics_summary_panel():
    source = _frontend_source()

    required_terms = [
        "Replay Analytics Summary Panel",
        "ReplayAnalyticsSummaryPanel",
        "replayAnalyticsSummary",
        "replayDistribution",
        "replayQualityScore",
        "candidate_count",
        "event_count",
        "time_window_min",
        "time_window_max",
        "best_quality_score",
        "worst_quality_score",
        "status distribution",
        "strategy distribution",
        "READ_ONLY_ANALYTICS",
        "Read-only replay analytics derived from the active filtered replay result set.",
    ]

    for term in required_terms:
        assert term in source

    assert "append=true" not in source
    for forbidden in ["Submit Order", "Modify Order", "Cancel Order", "Exit Order", "Approve Order", "Execute Order", "Place Order", "broker.place", "kite.place_order"]:
        assert forbidden not in source


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
from __future__ import annotations

from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
FRONTEND_MAIN = FRONTEND_DIR / "main.jsx"
MOVEMENT_PANEL = FRONTEND_DIR / "movementOpportunityPanel.jsx"


def _main_source() -> str:
    return FRONTEND_MAIN.read_text(encoding="utf-8")


def _panel_source() -> str:
    return MOVEMENT_PANEL.read_text(encoding="utf-8")


def _combined_source() -> str:
    return _main_source() + "\n" + _panel_source()


def test_movement_opportunity_panel_component_exists_and_is_wired():
    main_source = _main_source()
    panel_source = _panel_source()

    assert "from './movementOpportunityPanel.jsx'" in main_source
    assert "MovementOpportunityPanel" in main_source
    assert "export function MovementOpportunityPanel" in panel_source
    assert "Movement Opportunity Dashboard Read-only Panel" in panel_source


def test_movement_opportunity_panel_fetches_contract_endpoint():
    source = _combined_source()

    required_terms = [
        "DEFAULT_MOVEMENT_QUERY",
        "movementQuery",
        "movementOpportunity",
        "buildMovementOpportunityQueryString",
        "normalizeMovementQuery",
        "new URLSearchParams",
        "symbol",
        "ts_epoch",
        "`/movement-opportunity${movementQueryString}`",
        "Apply movement opportunity query",
        "Reset movement opportunity query",
    ]

    for term in required_terms:
        assert term in source


def test_movement_opportunity_panel_renders_pr69_contract_sections():
    source = _panel_source()

    required_terms = [
        "Movement API safety flags",
        "Movement summary",
        "Movement ranked candidates",
        "Movement rank records",
        "Movement exclusions",
        "Movement diagnostics",
        "movement opportunity raw payload",
        "api_schema_version",
        "ranked_candidates",
        "rank_records",
        "exclusions",
        "diagnostics",
        "pipeline.rank_result",
        "provider_count",
        "option_enriched_count",
        "allowed_count",
        "blocked_count",
        "no_trade_count",
        "top_candidate_id",
    ]

    for term in required_terms:
        assert term in source


def test_movement_opportunity_panel_exposes_safe_flags_visibly():
    source = _panel_source()

    required_terms = [
        "read_only",
        "is_order_action",
        "context.is_order_action",
        "summary.read_only",
        "summary.is_order_action",
        "pipeline.read_only",
        "pipeline.is_order_action",
        "Movement opportunity response is read-only and is_order_action=false across the public contract.",
        "READ_ONLY_MOVEMENT_OPPORTUNITY",
        "MOVEMENT_OPPORTUNITY_UNAVAILABLE",
        "movementSafeFlagWarnings",
        "MovementSafeFlagPanel",
    ]

    for term in required_terms:
        assert term in source


def test_movement_opportunity_panel_does_not_add_write_controls():
    source = _combined_source()

    forbidden_terms = [
        "Submit Movement",
        "Approve Movement",
        "Execute Movement",
        "Place Movement",
        "Modify Movement",
        "Cancel Movement",
        "Exit Movement",
        "append=true",
    ]

    for term in forbidden_terms:
        assert term not in source


def test_movement_opportunity_preferences_are_persisted_with_existing_control_tower_preferences():
    source = _main_source()

    required_terms = [
        "movementQuery: DEFAULT_MOVEMENT_QUERY",
        "normalizeMovementQuery(p.movementQuery || DEFAULT_MOVEMENT_QUERY)",
        "savePersistedPreferences({ filters, replayQuery, movementQuery, operatorView })",
        "setMovementQuery(DEFAULT_MOVEMENT_QUERY)",
        "Movement focus",
    ]

    for term in required_terms:
        assert term in source

from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_MAIN = FRONTEND_DIR / "main.jsx"
MOVEMENT_PANEL = FRONTEND_DIR / "movementOpportunityPanel.jsx"
MOVEMENT_FIXTURE_DIR = ROOT_DIR / "tests" / "fixtures" / "movement_opportunity"
MOVEMENT_FIXTURES = {
    "happy": MOVEMENT_FIXTURE_DIR / "happy_ranked_candidate.json",
    "empty": MOVEMENT_FIXTURE_DIR / "empty_no_candidate.json",
    "blocked": MOVEMENT_FIXTURE_DIR / "blocked_candidate.json",
}


def _main_source() -> str:
    return FRONTEND_MAIN.read_text(encoding="utf-8")


def _panel_source() -> str:
    return MOVEMENT_PANEL.read_text(encoding="utf-8")


def _combined_source() -> str:
    return _main_source() + "\n" + _panel_source()


def _fixture(name: str) -> dict:
    return json.loads(MOVEMENT_FIXTURES[name].read_text(encoding="utf-8"))


def _assert_public_safe_flags(payload: dict) -> None:
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["context"]["is_order_action"] is False
    assert payload["summary"]["read_only"] is True
    assert payload["summary"]["is_order_action"] is False
    assert payload["pipeline"]["read_only"] is True
    assert payload["pipeline"]["is_order_action"] is False
    assert payload["pipeline"]["summary"]["read_only"] is True
    assert payload["pipeline"]["summary"]["is_order_action"] is False
    assert payload["pipeline"]["rank_result"]["is_order_action"] is False
    for collection_name in ["ranked_candidates", "rank_records", "exclusions", "diagnostics"]:
        for item in payload[collection_name]:
            assert item["is_order_action"] is False, collection_name


def _movement_snapshot(payload: dict) -> dict:
    return {
        "route": payload["route"],
        "method": payload["method"],
        "read_only": payload["read_only"],
        "is_order_action": payload["is_order_action"],
        "symbol": payload["context"]["symbol"],
        "provider_count": payload["summary"]["provider_count"],
        "ranked_count": payload["summary"]["ranked_count"],
        "blocked_count": payload["summary"]["blocked_count"],
        "no_trade_count": payload["summary"]["no_trade_count"],
        "excluded_count": payload["summary"]["excluded_count"],
        "diagnostic_count": payload["summary"]["diagnostic_count"],
        "warning_count": payload["summary"]["warning_count"],
        "top_candidate_id": payload["summary"]["top_candidate_id"],
        "ranked_candidate_ids": [candidate["candidate_id"] for candidate in payload["ranked_candidates"]],
        "exclusion_ids": [exclusion["candidate_id"] for exclusion in payload["exclusions"]],
        "diagnostic_codes": [diagnostic["code"] for diagnostic in payload["diagnostics"]],
    }


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


def test_movement_fixture_files_exist():
    for path in MOVEMENT_FIXTURES.values():
        assert path.exists()


def test_movement_dashboard_fixtures_keep_pr69_top_level_contract():
    expected_keys = [
        "api_schema_version",
        "route",
        "method",
        "read_only",
        "is_order_action",
        "context",
        "summary",
        "ranked_candidates",
        "rank_records",
        "exclusions",
        "warnings",
        "diagnostics",
        "pipeline",
    ]
    for fixture_name in MOVEMENT_FIXTURES:
        payload = _fixture(fixture_name)
        assert list(payload.keys()) == expected_keys
        assert payload["route"] == "/movement-opportunity"
        assert payload["method"] == "GET"
        assert payload["api_schema_version"] == "1.0"
        _assert_public_safe_flags(payload)


def test_movement_dashboard_happy_fixture_snapshot_contract():
    snapshot = _movement_snapshot(_fixture("happy"))

    assert snapshot == {
        "route": "/movement-opportunity",
        "method": "GET",
        "read_only": True,
        "is_order_action": False,
        "symbol": "NIFTY",
        "provider_count": 6,
        "ranked_count": 1,
        "blocked_count": 0,
        "no_trade_count": 0,
        "excluded_count": 0,
        "diagnostic_count": 0,
        "warning_count": 0,
        "top_candidate_id": "move_nifty_opening_drive_001",
        "ranked_candidate_ids": ["move_nifty_opening_drive_001"],
        "exclusion_ids": [],
        "diagnostic_codes": [],
    }


def test_movement_dashboard_empty_fixture_snapshot_contract():
    snapshot = _movement_snapshot(_fixture("empty"))

    assert snapshot == {
        "route": "/movement-opportunity",
        "method": "GET",
        "read_only": True,
        "is_order_action": False,
        "symbol": "NIFTY",
        "provider_count": 6,
        "ranked_count": 0,
        "blocked_count": 0,
        "no_trade_count": 0,
        "excluded_count": 0,
        "diagnostic_count": 1,
        "warning_count": 1,
        "top_candidate_id": None,
        "ranked_candidate_ids": [],
        "exclusion_ids": [],
        "diagnostic_codes": ["NO_MOVEMENT_CANDIDATES"],
    }


def test_movement_dashboard_blocked_fixture_snapshot_contract():
    snapshot = _movement_snapshot(_fixture("blocked"))

    assert snapshot == {
        "route": "/movement-opportunity",
        "method": "GET",
        "read_only": True,
        "is_order_action": False,
        "symbol": "NIFTY",
        "provider_count": 6,
        "ranked_count": 0,
        "blocked_count": 2,
        "no_trade_count": 2,
        "excluded_count": 2,
        "diagnostic_count": 1,
        "warning_count": 1,
        "top_candidate_id": None,
        "ranked_candidate_ids": [],
        "exclusion_ids": ["move_nifty_failed_breakout_001", "move_nifty_vwap_reclaim_001"],
        "diagnostic_codes": ["ALL_MOVEMENT_CANDIDATES_BLOCKED"],
    }


def test_movement_panel_source_renders_fixture_backed_empty_and_blocked_states():
    source = _panel_source()

    required_empty_terms = [
        "no movement ranked candidates yet",
        "no movement rank records yet",
        "no movement exclusions yet",
        "no movement diagnostics yet",
    ]
    required_blocked_terms = [
        "Movement exclusions",
        "blockers",
        "blocked_count",
        "no_trade_count",
        "excluded_count",
    ]
    for term in required_empty_terms + required_blocked_terms:
        assert term in source


def test_movement_panel_source_renders_fixture_backed_ranked_candidate_columns():
    source = _panel_source()

    required_columns = [
        "candidate_id",
        "strategy_id",
        "movement_type",
        "direction",
        "status",
        "option_confirmation_score",
        "liquidity_score",
        "freshness_score",
        "is_order_action",
        "blockers",
        "warnings",
        "rank_score",
    ]
    for column in required_columns:
        assert column in source


def test_movement_fixtures_never_claim_order_action():
    for fixture_name in MOVEMENT_FIXTURES:
        serialized = MOVEMENT_FIXTURES[fixture_name].read_text(encoding="utf-8")
        assert '"is_order_action": true' not in serialized
        assert "broker_api_called" not in serialized
        assert "real_order_id" not in serialized

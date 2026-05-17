from __future__ import annotations

from pathlib import Path


FRONTEND_MAIN = Path(__file__).resolve().parents[1] / "frontend" / "main.jsx"
REPLAY_CONTRACT_DOC = Path(__file__).resolve().parents[1] / "docs" / "replay-contract-index.md"


def _frontend_source() -> str:
    return FRONTEND_MAIN.read_text(encoding="utf-8")


def test_replay_contract_health_badge_renders_static_registry():
    source = _frontend_source()

    required_terms = [
        "REPLAY_CONTRACT_HEALTH",
        "ReplayContractHealthBadge",
        "Replay Contract Health Badge",
        "REPLAY_CONTRACTS_INDEXED",
        "static_frontend_contract_registry",
        "Portfolio CI proves these files exist.",
        "docs/replay-contract-index.md",
        "index_doc",
        "doc_count",
        "test_count",
        "fixture_count",
        "contract docs",
        "contract tests",
        "contract fixtures",
    ]

    for term in required_terms:
        assert term in source


def test_replay_contract_health_badge_lists_replay_docs_tests_and_fixtures():
    source = _frontend_source()

    required_docs = [
        "docs/replay-contract-index.md",
        "docs/replay-query-api.md",
        "docs/replay-timeline-ui.md",
        "docs/replay-result-drilldown-ux.md",
        "docs/replay-analytics-summary-panel.md",
        "docs/replay-export-snapshot-panel.md",
        "docs/replay-evidence-regression-fixtures.md",
        "docs/replay-fixture-api-contract-tests.md",
        "docs/replay-fixture-ui-snapshot-contracts.md",
    ]
    required_tests = [
        "tests/test_outcome_replay_query.py",
        "tests/test_outcome_replay_api_query.py",
        "tests/test_replay_evidence_fixtures.py",
        "tests/test_replay_fixture_api_contracts.py",
        "tests/test_replay_fixture_ui_snapshot_contracts.py",
        "tests/test_control_tower_ui.py",
    ]
    required_fixtures = [
        "tests/fixtures/replay/empty_replay.json",
        "tests/fixtures/replay/single_candidate_lifecycle.json",
        "tests/fixtures/replay/multi_candidate_mixed_status.json",
    ]

    for term in required_docs + required_tests + required_fixtures:
        assert term in source


def test_replay_contract_health_badge_is_read_only_and_static():
    source = _frontend_source()

    assert "readOnly: true" in source
    assert "REPLAY_CONTRACTS_INDEXED" in source
    assert "ReplayContractHealthBadge" in source
    assert "fetch(`${API_BASE}${health" not in source
    assert "fetch(`${API_BASE}${REPLAY_CONTRACT_HEALTH" not in source
    assert "append=true" not in source

    forbidden_controls = [
        "Submit Order",
        "Modify Order",
        "Cancel Order",
        "Exit Order",
        "Approve Order",
        "Execute Order",
        "Place Order",
        "broker.place",
        "kite.place_order",
    ]
    for term in forbidden_controls:
        assert term not in source


def test_replay_contract_index_doc_exists_and_mentions_badge_contract():
    assert REPLAY_CONTRACT_DOC.is_file()
    doc = REPLAY_CONTRACT_DOC.read_text(encoding="utf-8")

    required_terms = [
        "Replay Contract Index",
        "Replay PR chain",
        "Test contract chain",
        "Safety boundary",
        "docs/replay-contract-index.md",
    ]

    for term in required_terms:
        assert term in doc

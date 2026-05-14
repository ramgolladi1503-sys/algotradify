from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import app
from opportunity_layer import run_opportunity_pipeline


def test_opportunity_pipeline_reports_empty_raw_count():
    result = run_opportunity_pipeline([], source="test")

    assert result.status == "NO_CANDIDATES"
    assert result.reason == "raw_count=0"
    assert result.counts["raw_count"] == 0
    assert result.counts["selected_count"] == 0
    assert result.selected is None
    assert result.is_execution_decision is False


def test_opportunity_pipeline_ranks_and_selects_top_candidate_without_execution_decision():
    result = run_opportunity_pipeline(
        [
            {
                "candidate_id": "low",
                "symbol": "NIFTY",
                "strategy_id": "orb_retest",
                "setup_family": "ORB_RETEST",
                "confidence": 60,
            },
            {
                "candidate_id": "high",
                "symbol": "NIFTY",
                "strategy_id": "vwap_reclaim",
                "setup_family": "VWAP_RECLAIM",
                "confidence": 90,
            },
        ],
        source="test",
    )

    assert result.status == "OPPORTUNITIES_AVAILABLE"
    assert result.reason is None
    assert result.counts["raw_count"] == 2
    assert result.counts["ranked_count"] == 2
    assert result.counts["selected_count"] == 1
    assert result.selected is not None
    assert result.selected.candidate_id == "high"
    assert result.selected.opportunity_status == "SELECTED"
    assert result.selected.selected is True
    assert result.selected.is_execution_decision is False
    assert result.ranked[0].candidate_id == "high"


def test_opportunity_pipeline_blocks_candidates_with_normal_blockers():
    result = run_opportunity_pipeline(
        [
            {
                "candidate_id": "blocked",
                "symbol": "NIFTY",
                "strategy_id": "orb_retest",
                "setup_family": "ORB_RETEST",
                "confidence": 70,
                "blockers": ["LOW_CONFIDENCE"],
            }
        ],
        source="test",
    )

    assert result.status == "NO_RANKABLE_CANDIDATES"
    assert result.reason == "no_execution_candidates"
    assert result.counts["blocked_count"] == 1
    assert result.blocked[0].candidate_id == "blocked"
    assert result.blocked[0].blockers == ["LOW_CONFIDENCE"]
    assert result.diagnostics["blocked_reasons"] == {"LOW_CONFIDENCE": 1}


def test_opportunity_pipeline_drops_malformed_and_synthetic_candidates():
    result = run_opportunity_pipeline(
        [
            {"symbol": "NIFTY"},
            {
                "candidate_id": "synthetic",
                "symbol": "NIFTY",
                "strategy_id": "demo",
                "setup_family": "DEMO",
                "is_synthetic": True,
            },
        ],
        source="test",
    )

    assert result.status == "NO_RANKABLE_CANDIDATES"
    assert result.counts["dropped_count"] == 2
    assert {row.candidate_id for row in result.dropped} == {"malformed:missing_candidate_id", "synthetic"}
    assert any("NON_RANKABLE_TRUTH_STATUS:MALFORMED" in row.blockers for row in result.dropped)
    assert any("NON_RANKABLE_TRUTH_STATUS:SYNTHETIC" in row.blockers for row in result.dropped)


def test_strategy_draft_opportunity_layer_api_selects_top_preview_candidate():
    client = TestClient(app)

    response = client.get(
        "/strategies/draft-candidates/opportunity-layer"
        "?symbol=nifty&orb_retest_score=85&vwap_reclaim_score=92"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "OPPORTUNITIES_AVAILABLE"
    assert payload["counts"]["raw_count"] == 2
    assert payload["counts"]["selected_count"] == 1
    assert payload["selected"]["candidate_id"] == "vwap_reclaim:NIFTY:na"
    assert payload["selected"]["is_execution_decision"] is False


def test_opportunity_layer_api_reports_empty_when_no_runtime_opportunities_exist(tmp_path, monkeypatch):
    import api.server as server

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)
    client = TestClient(app)

    response = client.get("/opportunity-layer")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NO_CANDIDATES"
    assert payload["reason"] == "raw_count=0"
    assert payload["counts"]["raw_count"] == 0
    assert payload["selected"] is None

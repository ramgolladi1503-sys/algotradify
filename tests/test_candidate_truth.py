from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import app
from candidate_truth import normalize_candidate
from strategies import StrategyContext, build_default_strategy_registry


def test_strategy_draft_normalizes_to_real_truth_record():
    registry = build_default_strategy_registry()
    draft = registry.generate_all(
        StrategyContext(symbol="NIFTY", timestamp_epoch=123, features={"orb_retest_score": 85}),
        strategy_ids=["orb_retest"],
    )[0]

    record = normalize_candidate(draft, source="test")

    assert record.truth_status == "REAL"
    assert record.candidate_id == "orb_retest:NIFTY:123"
    assert record.symbol == "NIFTY"
    assert record.strategy_id == "orb_retest"
    assert record.setup_family == "ORB_RETEST"
    assert record.is_execution_decision is False
    assert record.is_candidate_truth_record is True
    assert record.provenance["source"] == "strategies.simple_signal.ThresholdStrategy"


def test_fallback_candidate_is_classified_as_fallback():
    record = normalize_candidate(
        {
            "candidate_id": "c1",
            "symbol": "NIFTY",
            "strategy": "orb_retest",
            "strategy_family": "ORB_RETEST",
            "fallback_used": True,
            "warnings": ["nearest_contract_used"],
        },
        source="test",
    )

    assert record.truth_status == "FALLBACK"
    assert record.warnings == ["nearest_contract_used"]
    assert record.blockers == []


def test_synthetic_candidate_is_classified_as_synthetic():
    record = normalize_candidate(
        {
            "candidate_id": "demo-1",
            "symbol": "BANKNIFTY",
            "strategy": "mock_strategy",
            "strategy_family": "DEMO",
            "is_synthetic": True,
        },
        source="test",
    )

    assert record.truth_status == "SYNTHETIC"


def test_advisory_candidate_is_classified_as_advisory():
    record = normalize_candidate(
        {
            "candidate_id": "a1",
            "symbol": "SENSEX",
            "strategy": "range_reversion",
            "strategy_family": "RANGE_REVERSION",
            "final_action": "ADVISORY_ONLY",
        },
        source="test",
    )

    assert record.truth_status == "ADVISORY"


def test_missing_identity_fields_make_candidate_malformed():
    record = normalize_candidate({"symbol": "NIFTY"}, source="test")

    assert record.truth_status == "MALFORMED"
    assert "MISSING_CANDIDATE_ID" in record.blockers
    assert "MISSING_STRATEGY_ID" in record.blockers
    assert "MISSING_SETUP_FAMILY" in record.blockers
    assert record.candidate_id == "malformed:missing_candidate_id"


def test_normal_strategy_blocker_does_not_make_candidate_malformed():
    record = normalize_candidate(
        {
            "candidate_id": "c2",
            "symbol": "NIFTY",
            "strategy_id": "orb_retest",
            "setup_family": "ORB_RETEST",
            "entry_hypothesis": {},
            "blockers": ["LOW_CONFIDENCE"],
        },
        source="test",
    )

    assert record.truth_status == "REAL"
    assert record.blockers == ["LOW_CONFIDENCE"]


def test_draft_candidate_truth_api_returns_truth_records():
    client = TestClient(app)

    response = client.get("/strategies/draft-candidates/truth?symbol=nifty&orb_retest_score=85")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    record = payload[0]
    assert record["truth_status"] == "REAL"
    assert record["candidate_id"] == "orb_retest:NIFTY:na"
    assert record["is_candidate_truth_record"] is True
    assert record["is_execution_decision"] is False


def test_candidate_truth_api_returns_empty_when_no_opportunities_exist(tmp_path, monkeypatch):
    import api.server as server

    client = TestClient(app)
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(server, "_runtime_root", lambda: runtime_root)

    response = client.get("/candidate-truth")

    assert response.status_code == 200
    assert response.json() == []

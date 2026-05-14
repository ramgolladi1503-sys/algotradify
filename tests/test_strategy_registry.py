from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.server import app
from strategies import StrategyContext, build_default_strategy_registry
from strategies.base import StrategyCandidateDraft


def test_default_strategy_registry_lists_expected_strategies():
    registry = build_default_strategy_registry()
    strategies = registry.list()
    strategy_ids = {row["strategy_id"] for row in strategies}

    assert strategy_ids == {
        "orb_retest",
        "vwap_reclaim",
        "trend_pullback",
        "failed_breakout_reversal",
        "range_reversion",
        "expiry_momentum",
        "breadth_alignment",
    }
    assert all(row["required_data"] for row in strategies)


def test_strategy_generates_candidate_draft_not_execution_decision():
    registry = build_default_strategy_registry()
    context = StrategyContext(
        symbol="NIFTY",
        market_regime="TRENDING",
        timestamp_epoch=1234567890,
        features={"orb_retest_score": 85},
        raw={"source": "test"},
    )

    drafts = registry.generate_all(context, strategy_ids=["orb_retest"])

    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.candidate_id == "orb_retest:NIFTY:1234567890"
    assert draft.symbol == "NIFTY"
    assert draft.strategy_id == "orb_retest"
    assert draft.setup_family == "ORB_RETEST"
    assert draft.direction == "BULLISH"
    assert draft.confidence == 85
    assert draft.is_execution_decision is False
    assert "quote" in draft.required_data
    assert draft.to_dict()["is_execution_decision"] is False


def test_strategy_below_threshold_returns_no_draft():
    registry = build_default_strategy_registry()
    context = StrategyContext(symbol="NIFTY", features={"orb_retest_score": 20})

    drafts = registry.generate_all(context, strategy_ids=["orb_retest"])

    assert drafts == []


def test_candidate_draft_rejects_invalid_execution_like_shape():
    with pytest.raises(ValueError):
        StrategyCandidateDraft(
            candidate_id="bad",
            symbol="NIFTY",
            strategy_id="bad_strategy",
            setup_family="BAD",
            direction="EXECUTE",
            confidence=90,
            entry_hypothesis={},
            invalidation_hypothesis={},
        )


def test_strategies_api_lists_registry():
    client = TestClient(app)

    response = client.get("/strategies")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 7
    assert {row["strategy_id"] for row in payload} >= {"orb_retest", "vwap_reclaim"}


def test_strategy_draft_candidates_api_uses_query_features():
    client = TestClient(app)

    response = client.get("/strategies/draft-candidates?symbol=nifty&orb_retest_score=85")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    draft = payload[0]
    assert draft["candidate_id"] == "orb_retest:NIFTY:na"
    assert draft["symbol"] == "NIFTY"
    assert draft["strategy_id"] == "orb_retest"
    assert draft["confidence"] == 85
    assert draft["is_execution_decision"] is False

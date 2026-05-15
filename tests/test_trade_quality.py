from __future__ import annotations

from trade_quality import TradeQualityStatus, rank_trade_quality, score_trade_quality


def _execution_ready(candidate_id: str = "c1", **overrides):
    payload = {
        "candidate_id": candidate_id,
        "execution_allowed": True,
        "status": "ALLOWED",
        "blockers": [],
        "warnings": [],
        "evidence": {
            "candidate_truth": {
                "candidate_id": candidate_id,
                "truth_status": "REAL",
                "normalized": {"confidence": 90},
                "raw": {"confidence": 90},
            },
            "opportunity": {
                "candidate_id": candidate_id,
                "opportunity_status": "SELECTED",
                "rank_score": 90,
            },
            "broker_contract": {
                "candidate_id": candidate_id,
                "readiness_status": "RESOLVED_EXACT",
                "resolved": True,
                "fallback_used": False,
                "warnings": [],
            },
            "market_readiness": {
                "candidate_id": candidate_id,
                "status": "READY",
                "quote": {
                    "quote_age_sec": 0.2,
                    "max_quote_age_sec": 2.0,
                    "spread_pct": 0.1,
                    "max_spread_pct": 1.0,
                },
                "warnings": [],
            },
            "risk": {
                "allowed": True,
                "status": "RISK_OK",
                "warnings": [],
            },
        },
    }
    payload.update(overrides)
    return payload


def test_trade_quality_scores_allowed_candidate():
    result = score_trade_quality(_execution_ready())

    assert result.candidate_id == "c1"
    assert result.status == TradeQualityStatus.QUALIFIED
    assert result.quality_score > 80
    assert result.components["confidence"] == 22.5
    assert result.components["broker_contract"] == 20.0
    assert result.components["risk"] == 20.0
    assert result.blockers == []
    assert result.is_order is False


def test_trade_quality_blocked_candidate_scores_zero():
    result = score_trade_quality(
        {
            "candidate_id": "blocked",
            "execution_allowed": False,
            "status": "BLOCKED_MARKET_READINESS",
            "blockers": ["MARKET_NOT_READY:BLOCKED_STALE_QUOTE"],
            "warnings": [],
            "evidence": {},
        }
    )

    assert result.status == TradeQualityStatus.BLOCKED_NOT_EXECUTION_READY
    assert result.quality_score == 0.0
    assert result.blockers == ["MARKET_NOT_READY:BLOCKED_STALE_QUOTE"]
    assert result.is_order is False


def test_trade_quality_applies_fallback_penalty_and_warning_status():
    payload = _execution_ready()
    payload["warnings"] = ["BROKER_CONTRACT:FALLBACK_USED"]
    payload["evidence"]["broker_contract"]["readiness_status"] = "RESOLVED_FALLBACK"
    payload["evidence"]["broker_contract"]["fallback_used"] = True

    result = score_trade_quality(payload)

    assert result.status == TradeQualityStatus.DEGRADED_BY_WARNINGS
    assert result.components["broker_contract"] == 14.0
    assert result.penalties["broker_fallback"] == 5.0
    assert result.penalties["warnings"] == 2.0
    assert result.quality_score < score_trade_quality(_execution_ready()).quality_score


def test_trade_quality_rank_orders_by_quality_score():
    best = _execution_ready("best")
    weaker = _execution_ready("weaker")
    weaker["evidence"]["candidate_truth"]["normalized"]["confidence"] = 60
    weaker["evidence"]["market_readiness"]["quote"]["spread_pct"] = 0.8
    blocked = {
        "candidate_id": "blocked",
        "execution_allowed": False,
        "blockers": ["MISSING_RISK_READINESS"],
        "warnings": [],
        "evidence": {},
    }

    ranked = rank_trade_quality([weaker, blocked, best])

    assert [row.candidate_id for row in ranked] == ["best", "weaker", "blocked"]
    assert [row.rank for row in ranked] == [1, 2, 3]
    assert ranked[0].quality_score > ranked[1].quality_score > ranked[2].quality_score


def test_trade_quality_uses_default_components_when_optional_evidence_values_missing():
    payload = _execution_ready()
    payload["evidence"]["candidate_truth"] = {"candidate_id": "c1", "truth_status": "REAL"}
    payload["evidence"]["market_readiness"] = {"candidate_id": "c1", "status": "READY"}

    result = score_trade_quality(payload)

    assert result.quality_score > 0
    assert result.components["confidence"] == 10.0
    assert result.components["quote_freshness"] == 8.0
    assert result.components["liquidity"] == 12.0

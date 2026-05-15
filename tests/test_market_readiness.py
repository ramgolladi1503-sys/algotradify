from __future__ import annotations

from market_readiness import MarketReadinessStatus, evaluate_market_readiness, evaluate_market_readiness_batch


def _quote(**overrides):
    row = {
        "symbol": "NIFTY26MAY25500CE",
        "ltp": 100.0,
        "bid": 99.5,
        "ask": 100.5,
        "quote_age_sec": 0.5,
        "depth_age_sec": 0.7,
        "source": "websocket",
    }
    row.update(overrides)
    return row


def test_market_readiness_ready_for_fresh_tight_quote():
    result = evaluate_market_readiness(_quote(), max_spread_pct=2.0, slippage_budget_pct=2.5)

    assert result.status == MarketReadinessStatus.READY
    assert result.fresh_quote is True
    assert result.fresh_depth is True
    assert result.liquidity_ok is True
    assert result.slippage_budget_ok is True
    assert result.blockers == []
    assert result.quote["spread"] == 1.0
    assert result.quote["spread_pct"] == 1.0
    assert result.to_dict()["is_execution_decision"] is False


def test_market_readiness_blocks_stale_option_ltp():
    result = evaluate_market_readiness(_quote(quote_age_sec=4.0), max_quote_age_sec=2.0)

    assert result.status == MarketReadinessStatus.BLOCKED_STALE_QUOTE
    assert result.fresh_quote is False
    assert "STALE_OPTION_LTP" in result.blockers


def test_market_readiness_blocks_stale_depth():
    result = evaluate_market_readiness(_quote(depth_age_sec=5.0), max_depth_age_sec=2.0)

    assert result.status == MarketReadinessStatus.BLOCKED_STALE_DEPTH
    assert result.fresh_depth is False
    assert "STALE_DEPTH" in result.blockers


def test_market_readiness_blocks_wide_spread():
    result = evaluate_market_readiness(
        _quote(bid=95, ask=105, ltp=100),
        max_spread_pct=2.0,
        slippage_budget_pct=15.0,
    )

    assert result.status == MarketReadinessStatus.BLOCKED_SPREAD_TOO_WIDE
    assert result.liquidity_ok is False
    assert result.slippage_budget_ok is True
    assert "SPREAD_TOO_WIDE" in result.blockers


def test_market_readiness_blocks_slippage_budget():
    result = evaluate_market_readiness(
        _quote(bid=90, ask=110, ltp=100),
        max_spread_pct=25.0,
        slippage_budget_pct=5.0,
    )

    assert result.status == MarketReadinessStatus.BLOCKED_SLIPPAGE_BUDGET
    assert result.liquidity_ok is True
    assert result.slippage_budget_ok is False
    assert "SLIPPAGE_BUDGET_EXCEEDED" in result.blockers


def test_market_readiness_blocks_missing_quote():
    result = evaluate_market_readiness(None)

    assert result.status == MarketReadinessStatus.BLOCKED_MISSING_QUOTE
    assert result.symbol == "UNKNOWN"
    assert result.fresh_quote is False
    assert result.fresh_depth is False
    assert result.blockers == ["MISSING_QUOTE"]


def test_market_readiness_blocks_missing_bid_ask():
    result = evaluate_market_readiness(_quote(bid=None, ask=None))

    assert result.status == MarketReadinessStatus.BLOCKED_MISSING_QUOTE
    assert result.liquidity_ok is False
    assert "MISSING_BID_ASK" in result.blockers
    assert "SLIPPAGE_BUDGET_EXCEEDED" in result.blockers


def test_market_readiness_warns_when_source_missing():
    result = evaluate_market_readiness(_quote(source=""))

    assert result.status == MarketReadinessStatus.READY
    assert result.warnings == ["QUOTE_SOURCE_MISSING"]


def test_market_readiness_batch_evaluates_all_quotes():
    results = evaluate_market_readiness_batch([_quote(symbol="A"), _quote(symbol="B", quote_age_sec=9.0)])

    assert len(results) == 2
    assert results[0].status == MarketReadinessStatus.READY
    assert results[1].status == MarketReadinessStatus.BLOCKED_STALE_QUOTE

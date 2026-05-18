from __future__ import annotations

from market_readiness import (
    LiveMarketDataSnapshotStatus,
    MarketReadinessStatus,
    QuoteFreshnessMonitorStatus,
    build_live_market_data_snapshot,
    build_quote_freshness_runtime_monitor,
    evaluate_market_readiness,
    evaluate_market_readiness_batch,
    live_market_data_snapshot_schema_contract,
    quote_freshness_runtime_monitor_schema_contract,
)


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


def _live_snapshot_row(**overrides):
    row = {
        "symbol": "NIFTY",
        "spot_ltp": 22500.0,
        "spot_quote_age_sec": 0.8,
        "source": "PRIMARY",
        "session_state": "OPEN",
        "option_chain_age_sec": 2.0,
        "expiry": "WEEKLY",
        "ce_count": 120,
        "pe_count": 118,
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


def test_live_market_data_snapshot_schema_contract_is_safe_and_complete():
    contract = live_market_data_snapshot_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["snapshot_type"] == "LIVE_MARKET_DATA_SNAPSHOT"
    assert contract["safe_flags"] == {"read_only": True, "is_order_action": False}
    assert "spot" in contract["required_keys"]
    assert "option_chain" in contract["required_keys"]
    assert "read_only" in contract["required_keys"]
    assert "is_order_action" in contract["required_keys"]
    assert contract["default_thresholds"]["max_spot_quote_age_sec"] == 2.0
    assert contract["default_thresholds"]["max_option_chain_age_sec"] == 5.0


def test_live_market_data_snapshot_ready_for_fresh_primary_open_session():
    result = build_live_market_data_snapshot(_live_snapshot_row())
    payload = result.to_dict()

    assert result.status == LiveMarketDataSnapshotStatus.READY
    assert payload["snapshot_type"] == "LIVE_MARKET_DATA_SNAPSHOT"
    assert payload["symbol"] == "NIFTY"
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["spot_quote_fresh"] is True
    assert payload["option_chain_fresh"] is True
    assert payload["source_reliable"] is True
    assert payload["session_open"] is True
    assert payload["blockers"] == []
    assert payload["spot"]["ltp"] == 22500.0
    assert payload["option_chain"]["ce_count"] == 120
    assert payload["option_chain"]["pe_count"] == 118


def test_live_market_data_snapshot_blocks_stale_spot_quote():
    result = build_live_market_data_snapshot(_live_snapshot_row(spot_quote_age_sec=7.5))

    assert result.status == LiveMarketDataSnapshotStatus.BLOCKED_STALE_SPOT
    assert result.spot_quote_fresh is False
    assert "STALE_SPOT_QUOTE" in result.blockers
    assert result.to_dict()["read_only"] is True
    assert result.to_dict()["is_order_action"] is False


def test_live_market_data_snapshot_blocks_missing_spot():
    result = build_live_market_data_snapshot(_live_snapshot_row(spot_ltp=None))

    assert result.status == LiveMarketDataSnapshotStatus.BLOCKED_MISSING_SPOT
    assert result.spot_quote_fresh is False
    assert "MISSING_SPOT_LTP" in result.blockers
    assert result.to_dict()["spot"]["ltp"] is None


def test_live_market_data_snapshot_blocks_fallback_source():
    result = build_live_market_data_snapshot(_live_snapshot_row(source="FALLBACK"))

    assert result.status == LiveMarketDataSnapshotStatus.BLOCKED_FALLBACK_SOURCE
    assert result.source_reliable is False
    assert "UNRELIABLE_MARKET_DATA_SOURCE" in result.blockers
    assert result.to_dict()["source"] == "FALLBACK"


def test_live_market_data_snapshot_blocks_missing_option_chain():
    result = build_live_market_data_snapshot(
        _live_snapshot_row(option_chain_age_sec=None, expiry=None, ce_count=None, pe_count=None)
    )

    assert result.status == LiveMarketDataSnapshotStatus.BLOCKED_MISSING_OPTION_CHAIN
    assert result.option_chain_fresh is False
    assert "MISSING_OPTION_CHAIN" in result.blockers
    assert result.to_dict()["option_chain"]["age_sec"] is None


def test_live_market_data_snapshot_blocks_stale_option_chain():
    result = build_live_market_data_snapshot(_live_snapshot_row(option_chain_age_sec=15.0))

    assert result.status == LiveMarketDataSnapshotStatus.BLOCKED_STALE_OPTION_CHAIN
    assert result.option_chain_fresh is False
    assert "STALE_OPTION_CHAIN" in result.blockers


def test_live_market_data_snapshot_blocks_closed_session_after_data_quality_checks_pass():
    result = build_live_market_data_snapshot(_live_snapshot_row(session_state="CLOSED"))

    assert result.status == LiveMarketDataSnapshotStatus.BLOCKED_SESSION_CLOSED
    assert result.session_open is False
    assert "MARKET_SESSION_NOT_OPEN" in result.blockers


def test_live_market_data_snapshot_warns_for_zero_option_side_counts_without_becoming_order_action():
    result = build_live_market_data_snapshot(_live_snapshot_row(ce_count=0, pe_count=0))
    payload = result.to_dict()

    assert "OPTION_CHAIN_SIDE_COUNT_ZERO" in payload["warnings"]
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False


def test_quote_freshness_runtime_monitor_schema_contract_is_safe_and_complete():
    contract = quote_freshness_runtime_monitor_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["monitor_type"] == "QUOTE_FRESHNESS_RUNTIME_MONITOR"
    assert contract["safe_flags"] == {"read_only": True, "is_order_action": False}
    assert "summary" in contract["required_keys"]
    assert "snapshots" in contract["required_keys"]
    assert "fresh_ratio" in contract["summary_required_keys"]
    assert "blocked_count" in contract["summary_required_keys"]


def test_quote_freshness_runtime_monitor_is_healthy_for_all_fresh_snapshots():
    result = build_quote_freshness_runtime_monitor([
        _live_snapshot_row(symbol="NIFTY"),
        _live_snapshot_row(symbol="BANKNIFTY"),
    ])
    payload = result.to_dict()

    assert result.status == QuoteFreshnessMonitorStatus.HEALTHY
    assert payload["monitor_type"] == "QUOTE_FRESHNESS_RUNTIME_MONITOR"
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["summary"]["snapshot_count"] == 2
    assert payload["summary"]["ready_count"] == 2
    assert payload["summary"]["blocked_count"] == 0
    assert payload["summary"]["fresh_ratio"] == 1.0
    assert payload["blockers"] == []
    assert len(payload["snapshots"]) == 2


def test_quote_freshness_runtime_monitor_blocks_stale_quotes():
    result = build_quote_freshness_runtime_monitor([
        _live_snapshot_row(symbol="NIFTY", spot_quote_age_sec=8.0),
        _live_snapshot_row(symbol="BANKNIFTY"),
    ])
    payload = result.to_dict()

    assert result.status == QuoteFreshnessMonitorStatus.BLOCKED
    assert payload["summary"]["snapshot_count"] == 2
    assert payload["summary"]["ready_count"] == 1
    assert payload["summary"]["stale_spot_count"] == 1
    assert payload["summary"]["blocked_count"] == 1
    assert payload["summary"]["fresh_ratio"] == 0.5
    assert "STALE_SPOT_QUOTES_PRESENT" in payload["blockers"]


def test_quote_freshness_runtime_monitor_blocks_missing_quote_data():
    result = build_quote_freshness_runtime_monitor([
        _live_snapshot_row(symbol="NIFTY", spot_ltp=None),
    ])
    payload = result.to_dict()

    assert result.status == QuoteFreshnessMonitorStatus.BLOCKED
    assert payload["summary"]["missing_spot_count"] == 1
    assert "MISSING_SPOT_DATA_PRESENT" in payload["blockers"]
    assert payload["snapshots"][0]["read_only"] is True
    assert payload["snapshots"][0]["is_order_action"] is False


def test_quote_freshness_runtime_monitor_blocks_fallback_source():
    result = build_quote_freshness_runtime_monitor([
        _live_snapshot_row(symbol="NIFTY", source="FALLBACK"),
    ])
    payload = result.to_dict()

    assert result.status == QuoteFreshnessMonitorStatus.BLOCKED
    assert payload["summary"]["fallback_source_count"] == 1
    assert "FALLBACK_MARKET_DATA_SOURCE_PRESENT" in payload["blockers"]


def test_quote_freshness_runtime_monitor_blocks_closed_session():
    result = build_quote_freshness_runtime_monitor([
        _live_snapshot_row(symbol="NIFTY", session_state="CLOSED"),
    ])
    payload = result.to_dict()

    assert result.status == QuoteFreshnessMonitorStatus.BLOCKED
    assert payload["summary"]["closed_session_count"] == 1
    assert "MARKET_SESSION_CLOSED_PRESENT" in payload["blockers"]


def test_quote_freshness_runtime_monitor_blocks_missing_and_stale_option_chain():
    result = build_quote_freshness_runtime_monitor([
        _live_snapshot_row(symbol="NIFTY", option_chain_age_sec=None, expiry=None, ce_count=None, pe_count=None),
        _live_snapshot_row(symbol="BANKNIFTY", option_chain_age_sec=15.0),
    ])
    payload = result.to_dict()

    assert result.status == QuoteFreshnessMonitorStatus.BLOCKED
    assert payload["summary"]["missing_option_chain_count"] == 1
    assert payload["summary"]["stale_option_chain_count"] == 1
    assert "MISSING_OPTION_CHAIN_PRESENT" in payload["blockers"]
    assert "STALE_OPTION_CHAIN_PRESENT" in payload["blockers"]


def test_quote_freshness_runtime_monitor_is_empty_when_no_snapshots_exist():
    result = build_quote_freshness_runtime_monitor([])
    payload = result.to_dict()

    assert result.status == QuoteFreshnessMonitorStatus.EMPTY
    assert payload["summary"]["snapshot_count"] == 0
    assert payload["summary"]["fresh_ratio"] == 0.0
    assert "NO_MARKET_DATA_SNAPSHOTS" in payload["blockers"]
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False


def test_quote_freshness_runtime_monitor_degrades_on_snapshot_warnings_only():
    result = build_quote_freshness_runtime_monitor([
        _live_snapshot_row(symbol="NIFTY", ce_count=0, pe_count=0),
    ])
    payload = result.to_dict()

    assert result.status == QuoteFreshnessMonitorStatus.DEGRADED
    assert payload["summary"]["warning_count"] == 1
    assert payload["summary"]["blocked_count"] == 0
    assert "SNAPSHOT_WARNINGS_PRESENT" in payload["warnings"]
    assert "NIFTY:OPTION_CHAIN_SIDE_COUNT_ZERO" in payload["warnings"]


def test_quote_freshness_runtime_monitor_accepts_prebuilt_snapshots():
    snapshot = build_live_market_data_snapshot(_live_snapshot_row(symbol="NIFTY"))
    result = build_quote_freshness_runtime_monitor([snapshot])

    assert result.status == QuoteFreshnessMonitorStatus.HEALTHY
    assert result.snapshots[0] is snapshot
    assert result.to_dict()["summary"]["ready_count"] == 1

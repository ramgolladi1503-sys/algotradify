from __future__ import annotations

from market_readiness import (
    LiveMarketDataSnapshotStatus,
    MarketReadinessStatus,
    MarketSessionExpiryGuardStatus,
    OptionChainDepthQualityStatus,
    QuoteFreshnessMonitorStatus,
    build_live_market_data_snapshot,
    build_market_session_expiry_guard,
    build_option_chain_depth_quality_monitor,
    build_quote_freshness_runtime_monitor,
    evaluate_market_readiness,
    evaluate_market_readiness_batch,
    live_market_data_snapshot_schema_contract,
    market_session_expiry_guard_schema_contract,
    option_chain_depth_quality_schema_contract,
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


def _option_depth_row(**overrides):
    row = {
        "ce_count": 120,
        "pe_count": 118,
        "ce_depth": 850.0,
        "pe_depth": 760.0,
        "depth_age_sec": 1.2,
    }
    row.update(overrides)
    return row


def _session_expiry_row(**overrides):
    row = {
        "session_state": "OPEN",
        "expiry": "2026-05-21",
        "expiry_type": "WEEKLY",
        "trade_date": "2026-05-18",
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


def test_option_chain_depth_quality_schema_contract_is_safe_and_complete():
    contract = option_chain_depth_quality_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["monitor_type"] == "OPTION_CHAIN_DEPTH_QUALITY_MONITOR"
    assert contract["safe_flags"] == {"read_only": True, "is_order_action": False}
    assert "summary" in contract["required_keys"]
    assert "side_quality" in contract["required_keys"]
    assert "imbalance_ratio" in contract["summary_required_keys"]
    assert "ce_available" in contract["side_quality_required_keys"]
    assert contract["default_thresholds"]["min_side_count"] == 1
    assert contract["default_thresholds"]["min_total_depth"] == 100.0


def test_option_chain_depth_quality_monitor_is_healthy_for_balanced_fresh_depth():
    result = build_option_chain_depth_quality_monitor(_option_depth_row())
    payload = result.to_dict()

    assert result.status == OptionChainDepthQualityStatus.HEALTHY
    assert payload["monitor_type"] == "OPTION_CHAIN_DEPTH_QUALITY_MONITOR"
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["summary"]["ce_count"] == 120
    assert payload["summary"]["pe_count"] == 118
    assert payload["summary"]["total_depth"] == 1610.0
    assert payload["summary"]["missing_side_count"] == 0
    assert payload["summary"]["zero_side_count"] == 0
    assert payload["summary"]["shallow_depth_count"] == 0
    assert payload["summary"]["stale_depth_count"] == 0
    assert payload["summary"]["imbalance_count"] == 0
    assert payload["side_quality"]["ce_available"] is True
    assert payload["side_quality"]["pe_available"] is True
    assert payload["side_quality"]["depth_fresh"] is True
    assert payload["blockers"] == []


def test_option_chain_depth_quality_monitor_blocks_missing_side():
    result = build_option_chain_depth_quality_monitor(_option_depth_row(ce_count=None))
    payload = result.to_dict()

    assert result.status == OptionChainDepthQualityStatus.BLOCKED_MISSING_SIDE
    assert payload["summary"]["missing_side_count"] == 1
    assert "MISSING_CE_SIDE_COUNT" in payload["blockers"]
    assert payload["side_quality"]["ce_available"] is False
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False


def test_option_chain_depth_quality_monitor_blocks_zero_side():
    result = build_option_chain_depth_quality_monitor(_option_depth_row(pe_count=0))
    payload = result.to_dict()

    assert result.status == OptionChainDepthQualityStatus.BLOCKED_ZERO_SIDE
    assert payload["summary"]["zero_side_count"] == 1
    assert "ZERO_PE_SIDE_COUNT" in payload["blockers"]
    assert payload["side_quality"]["pe_available"] is False


def test_option_chain_depth_quality_monitor_blocks_shallow_depth():
    result = build_option_chain_depth_quality_monitor(_option_depth_row(ce_depth=20.0, pe_depth=25.0), min_total_depth=100.0)
    payload = result.to_dict()

    assert result.status == OptionChainDepthQualityStatus.BLOCKED_SHALLOW_DEPTH
    assert payload["summary"]["total_depth"] == 45.0
    assert payload["summary"]["shallow_depth_count"] == 1
    assert "TOTAL_DEPTH_BELOW_MINIMUM" in payload["blockers"]


def test_option_chain_depth_quality_monitor_blocks_stale_depth():
    result = build_option_chain_depth_quality_monitor(_option_depth_row(depth_age_sec=9.5), max_depth_age_sec=5.0)
    payload = result.to_dict()

    assert result.status == OptionChainDepthQualityStatus.BLOCKED_STALE_DEPTH
    assert payload["summary"]["stale_depth_count"] == 1
    assert "STALE_OPTION_DEPTH" in payload["blockers"]
    assert payload["side_quality"]["depth_fresh"] is False


def test_option_chain_depth_quality_monitor_blocks_depth_imbalance():
    result = build_option_chain_depth_quality_monitor(_option_depth_row(ce_depth=900.0, pe_depth=100.0), max_imbalance_ratio=3.0)
    payload = result.to_dict()

    assert result.status == OptionChainDepthQualityStatus.BLOCKED_DEPTH_IMBALANCE
    assert payload["summary"]["imbalance_count"] == 1
    assert payload["summary"]["imbalance_ratio"] == 9.0
    assert "OPTION_DEPTH_IMBALANCE" in payload["blockers"]
    assert payload["side_quality"]["imbalance_ok"] is False


def test_option_chain_depth_quality_monitor_empty_when_no_depth_data():
    result = build_option_chain_depth_quality_monitor(None)
    payload = result.to_dict()

    assert result.status == OptionChainDepthQualityStatus.EMPTY
    assert "NO_OPTION_CHAIN_DEPTH_DATA" in payload["blockers"]
    assert payload["summary"]["missing_side_count"] == 2
    assert payload["summary"]["shallow_depth_count"] == 3
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False


def test_option_chain_depth_quality_monitor_warns_when_imbalance_unavailable():
    result = build_option_chain_depth_quality_monitor(_option_depth_row(ce_depth=0.0, pe_depth=760.0))
    payload = result.to_dict()

    assert "DEPTH_IMBALANCE_UNAVAILABLE" in payload["warnings"]
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False


def test_market_session_expiry_guard_schema_contract_is_safe_and_complete():
    contract = market_session_expiry_guard_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["guard_type"] == "MARKET_SESSION_EXPIRY_CONTEXT_GUARD"
    assert contract["safe_flags"] == {"read_only": True, "is_order_action": False}
    assert "session_state" in contract["required_keys"]
    assert "expiry" in contract["required_keys"]
    assert "days_to_expiry" in contract["required_keys"]
    assert contract["default_thresholds"]["near_expiry_days"] == 1


def test_market_session_expiry_guard_ready_for_open_valid_future_expiry():
    result = build_market_session_expiry_guard(_session_expiry_row(), today="2026-05-18")
    payload = result.to_dict()

    assert result.status == MarketSessionExpiryGuardStatus.READY
    assert payload["guard_type"] == "MARKET_SESSION_EXPIRY_CONTEXT_GUARD"
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["session_open"] is True
    assert payload["expiry_valid"] is True
    assert payload["contract_expired"] is False
    assert payload["near_expiry"] is False
    assert payload["days_to_expiry"] == 3
    assert payload["blockers"] == []


def test_market_session_expiry_guard_blocks_pre_open_session():
    result = build_market_session_expiry_guard(_session_expiry_row(session_state="PRE_OPEN"), today="2026-05-18")
    payload = result.to_dict()

    assert result.status == MarketSessionExpiryGuardStatus.BLOCKED_PRE_OPEN
    assert payload["session_open"] is False
    assert "MARKET_SESSION_PRE_OPEN" in payload["blockers"]


def test_market_session_expiry_guard_blocks_closing_session():
    result = build_market_session_expiry_guard(_session_expiry_row(session_state="CLOSING"), today="2026-05-18")
    payload = result.to_dict()

    assert result.status == MarketSessionExpiryGuardStatus.BLOCKED_CLOSING
    assert payload["session_open"] is False
    assert "MARKET_SESSION_CLOSING" in payload["blockers"]


def test_market_session_expiry_guard_blocks_closed_session():
    result = build_market_session_expiry_guard(_session_expiry_row(session_state="CLOSED"), today="2026-05-18")
    payload = result.to_dict()

    assert result.status == MarketSessionExpiryGuardStatus.BLOCKED_CLOSED
    assert payload["session_open"] is False
    assert "MARKET_SESSION_CLOSED" in payload["blockers"]


def test_market_session_expiry_guard_blocks_expired_contract():
    result = build_market_session_expiry_guard(_session_expiry_row(expiry="2026-05-16"), today="2026-05-18")
    payload = result.to_dict()

    assert result.status == MarketSessionExpiryGuardStatus.BLOCKED_EXPIRED_CONTRACT
    assert payload["expiry_valid"] is False
    assert payload["contract_expired"] is True
    assert payload["days_to_expiry"] == -2
    assert "EXPIRED_CONTRACT" in payload["blockers"]


def test_market_session_expiry_guard_blocks_invalid_expiry():
    result = build_market_session_expiry_guard(_session_expiry_row(expiry="not-a-date"), today="2026-05-18")
    payload = result.to_dict()

    assert result.status == MarketSessionExpiryGuardStatus.BLOCKED_INVALID_EXPIRY
    assert payload["expiry_valid"] is False
    assert payload["days_to_expiry"] is None
    assert "INVALID_EXPIRY" in payload["blockers"]


def test_market_session_expiry_guard_blocks_missing_context():
    result = build_market_session_expiry_guard({"session_state": "", "expiry": ""}, today="2026-05-18")
    payload = result.to_dict()

    assert result.status == MarketSessionExpiryGuardStatus.BLOCKED_MISSING_CONTEXT
    assert "MISSING_MARKET_SESSION_STATE" in payload["blockers"]
    assert "MISSING_EXPIRY" in payload["blockers"]
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False


def test_market_session_expiry_guard_degrades_near_expiry_warning_only():
    result = build_market_session_expiry_guard(_session_expiry_row(expiry="2026-05-19"), today="2026-05-18")
    payload = result.to_dict()

    assert result.status == MarketSessionExpiryGuardStatus.DEGRADED_NEAR_EXPIRY
    assert payload["near_expiry"] is True
    assert payload["expiry_valid"] is True
    assert payload["blockers"] == []
    assert "NEAR_EXPIRY_CONTRACT" in payload["warnings"]


def test_market_session_expiry_guard_warns_unknown_expiry_type_without_blocking():
    result = build_market_session_expiry_guard(_session_expiry_row(expiry_type="ODD"), today="2026-05-18")
    payload = result.to_dict()

    assert result.status == MarketSessionExpiryGuardStatus.READY
    assert payload["expiry_type"] == "UNKNOWN"
    assert payload["blockers"] == []
    assert "EXPIRY_TYPE_UNKNOWN" in payload["warnings"]
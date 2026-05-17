from __future__ import annotations

import ast
import inspect

import movement_engine.providers.compression_trend as provider_module
from movement_engine import (
    CandidateStatus,
    Direction,
    MovementStrategyRegistry,
    StrategyContext,
    build_compression_trend_candidate_pool,
    compression_breakout_provider,
    register_compression_trend_providers,
    trend_pullback_provider,
    validate_strategy_candidate,
)


def _context(**overrides) -> StrategyContext:
    payload = {
        "symbol": "NIFTY",
        "ts_epoch": 22222.0,
        "spot_ltp": 102.2,
        "vwap": 101.8,
        "day_high": 102.0,
        "day_low": 100.0,
        "atr": 1.0,
        "atr_short": 0.6,
        "atr_long": 1.0,
        "range_width_pct": 0.35,
        "volume_z": 1.8,
        "volatility_state": "COMPRESSION",
        "regime_hint": "COMPRESSION",
        "option_ce_ltp": 130.0,
        "option_pe_ltp": 90.0,
        "ce_premium_change": 16.0,
        "pe_premium_change": -5.0,
        "ce_spread_pct": 1.0,
        "pe_spread_pct": 1.2,
        "ce_depth": 600.0,
        "pe_depth": 500.0,
        "option_ltp_age_sec": 1.0,
        "quote_source": "PRIMARY",
        "time_of_day": "OPEN",
    }
    payload.update(overrides)
    return StrategyContext(**payload)


def test_compression_breakout_provider_returns_valid_raw_buy_call_candidate():
    candidate = compression_breakout_provider(_context())[0]
    result = validate_strategy_candidate(candidate)

    assert candidate.strategy_id == "COMPRESSION_BREAKOUT"
    assert candidate.movement_type == "COMPRESSION_BREAKOUT"
    assert candidate.direction == Direction.BUY_CALL
    assert candidate.status == CandidateStatus.RAW_CANDIDATE
    assert candidate.raw_score > 0.0
    assert candidate.blockers == ()
    assert candidate.evidence["provider"] == "COMPRESSION_BREAKOUT"
    assert candidate.evidence["atr_ratio"] == 0.6
    assert candidate.is_order_action is False
    assert result.valid is True


def test_compression_breakout_provider_detects_downside_breakout():
    candidate = compression_breakout_provider(
        _context(
            spot_ltp=99.6,
            vwap=100.1,
            ce_premium_change=-4.0,
            pe_premium_change=18.0,
            regime_hint="COMPRESSION",
        )
    )[0]

    assert candidate.direction == Direction.BUY_PUT
    assert candidate.raw_score > 0.0
    assert candidate.evidence["breakout_direction"] == "BUY_PUT"


def test_compression_breakout_not_triggered_returns_diagnostic_candidate():
    candidate = compression_breakout_provider(_context(spot_ltp=101.0, volume_z=0.2))[0]

    assert "COMPRESSION_BREAKOUT_NOT_TRIGGERED" in candidate.blockers
    assert candidate.raw_score == 0.0
    assert validate_strategy_candidate(candidate).valid is True


def test_trend_pullback_provider_returns_valid_raw_buy_call_candidate():
    candidate = trend_pullback_provider(
        _context(
            spot_ltp=101.9,
            vwap=101.7,
            day_high=103.0,
            day_low=99.0,
            regime_hint="TREND_UP",
            volatility_state="TREND_UP",
            range_width_pct=0.8,
            atr_short=1.2,
            atr_long=1.0,
            volume_z=0.7,
            ce_premium_change=18.0,
            pe_premium_change=2.0,
        )
    )[0]
    result = validate_strategy_candidate(candidate)

    assert candidate.strategy_id == "TREND_PULLBACK"
    assert candidate.movement_type == "TREND_PULLBACK_CONTINUATION"
    assert candidate.direction == Direction.BUY_CALL
    assert candidate.status == CandidateStatus.RAW_CANDIDATE
    assert candidate.raw_score > 0.0
    assert candidate.blockers == ()
    assert candidate.evidence["provider"] == "TREND_PULLBACK"
    assert candidate.is_order_action is False
    assert result.valid is True


def test_trend_pullback_provider_detects_downside_pullback():
    candidate = trend_pullback_provider(
        _context(
            spot_ltp=100.1,
            vwap=100.3,
            day_high=103.0,
            day_low=99.0,
            regime_hint="TREND_DOWN",
            volatility_state="TREND_DOWN",
            range_width_pct=0.8,
            atr_short=1.2,
            atr_long=1.0,
            ce_premium_change=-2.0,
            pe_premium_change=16.0,
        )
    )[0]

    assert candidate.direction == Direction.BUY_PUT
    assert candidate.raw_score > 0.0
    assert candidate.evidence["pullback_direction"] == "BUY_PUT"


def test_trend_pullback_not_triggered_returns_diagnostic_candidate():
    candidate = trend_pullback_provider(
        _context(
            spot_ltp=104.5,
            vwap=101.0,
            regime_hint="RANGE",
            ce_premium_change=1.0,
            pe_premium_change=1.0,
        )
    )[0]

    assert "TREND_PULLBACK_NOT_TRIGGERED" in candidate.blockers
    assert candidate.raw_score == 0.0
    assert validate_strategy_candidate(candidate).valid is True


def test_compression_trend_providers_register_through_registry():
    registry = register_compression_trend_providers(MovementStrategyRegistry())
    result = registry.run(_context())

    assert registry.strategy_ids == ("COMPRESSION_BREAKOUT", "TREND_PULLBACK")
    assert result.provider_count == 2
    assert len(result.candidates) == 2
    assert {candidate.strategy_id for candidate in result.candidates} == {"COMPRESSION_BREAKOUT", "TREND_PULLBACK"}
    assert result.is_order_action is False


def test_compression_trend_candidate_pool_blocks_wide_spread():
    result = build_compression_trend_candidate_pool(_context(ce_spread_pct=4.0))
    compression = next(candidate for candidate in result.candidates if candidate.strategy_id == "COMPRESSION_BREAKOUT")

    assert compression.status == CandidateStatus.BLOCKED_CANDIDATE
    assert "WIDE_SPREAD" in compression.blockers
    assert compression.evidence["pool_hard_blockers"] == ["WIDE_SPREAD"]
    assert result.summary.blocked_count >= 1
    assert result.is_order_action is False


def test_compression_trend_candidate_pool_blocks_stale_ltp():
    result = build_compression_trend_candidate_pool(_context(option_ltp_age_sec=9.0))

    assert all(candidate.status == CandidateStatus.BLOCKED_CANDIDATE for candidate in result.candidates)
    assert all("STALE_OPTION_LTP" in candidate.blockers for candidate in result.candidates)
    assert result.summary.valid_count == 0


def test_candidate_pool_preserves_compression_trend_evidence():
    result = build_compression_trend_candidate_pool(_context())
    compression = next(candidate for candidate in result.candidates if candidate.strategy_id == "COMPRESSION_BREAKOUT")

    assert compression.evidence["provider"] == "COMPRESSION_BREAKOUT"
    assert compression.evidence["day_high"] == 102.0
    assert compression.evidence["day_low"] == 100.0
    assert compression.evidence["range_width_pct"] == 0.35
    assert compression.evidence["ce_depth"] == 600.0


def test_chop_regime_hard_blocks_compression_trend_pool():
    result = build_compression_trend_candidate_pool(_context(regime_hint="CHOP"))

    assert all(candidate.status == CandidateStatus.BLOCKED_CANDIDATE for candidate in result.candidates)
    assert all("NO_TRADE_CHOP" in candidate.blockers for candidate in result.candidates)
    assert result.summary.blocked_count == 2
    assert result.summary.valid_count == 0


def test_all_compression_trend_outputs_remain_non_order_actions():
    result = build_compression_trend_candidate_pool(_context())
    payload = result.to_dict()

    assert payload["is_order_action"] is False
    assert payload["summary"]["is_order_action"] is False
    assert all(candidate["is_order_action"] is False for candidate in payload["candidates"])


def test_compression_trend_providers_do_not_import_broker_order_api_or_dashboard_modules():
    forbidden_import_roots = {
        "api",
        "broker_contract",
        "dashboard",
        "order_intent",
        "paper_broker",
    }

    tree = ast.parse(inspect.getsource(provider_module))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint(forbidden_import_roots)

from __future__ import annotations

import ast
import inspect

import movement_engine.providers.vwap_trap as provider_module
from movement_engine import (
    CandidateStatus,
    Direction,
    MovementStrategyRegistry,
    StrategyContext,
    build_vwap_trap_candidate_pool,
    failed_breakout_trap_provider,
    register_vwap_trap_providers,
    validate_strategy_candidate,
    vwap_reclaim_provider,
)


def _context(**overrides) -> StrategyContext:
    payload = {
        "symbol": "NIFTY",
        "ts_epoch": 33333.0,
        "spot_ltp": 100.4,
        "vwap": 100.0,
        "day_high": 102.0,
        "day_low": 98.0,
        "orb_high": 101.8,
        "orb_low": 98.2,
        "prev_day_high": 102.4,
        "prev_day_low": 97.8,
        "atr": 1.1,
        "atr_short": 1.2,
        "atr_long": 1.0,
        "range_width_pct": 0.9,
        "volume_z": 1.1,
        "volatility_state": "VOLATILITY_EXPANSION",
        "regime_hint": "RANGE",
        "option_ce_ltp": 115.0,
        "option_pe_ltp": 95.0,
        "ce_premium_change": 14.0,
        "pe_premium_change": 2.0,
        "ce_spread_pct": 1.0,
        "pe_spread_pct": 1.1,
        "ce_depth": 550.0,
        "pe_depth": 500.0,
        "option_ltp_age_sec": 1.0,
        "quote_source": "PRIMARY",
        "time_of_day": "OPEN",
    }
    payload.update(overrides)
    return StrategyContext(**payload)


def test_vwap_reclaim_provider_returns_valid_raw_buy_call_candidate():
    candidate = vwap_reclaim_provider(_context())[0]
    result = validate_strategy_candidate(candidate)

    assert candidate.strategy_id == "VWAP_RECLAIM"
    assert candidate.movement_type == "VWAP_RECLAIM"
    assert candidate.direction == Direction.BUY_CALL
    assert candidate.status == CandidateStatus.RAW_CANDIDATE
    assert candidate.raw_score > 0.0
    assert candidate.blockers == ()
    assert candidate.evidence["provider"] == "VWAP_RECLAIM"
    assert candidate.evidence["vwap"] == 100.0
    assert candidate.is_order_action is False
    assert result.valid is True


def test_vwap_reclaim_provider_detects_vwap_loss_buy_put_candidate():
    candidate = vwap_reclaim_provider(
        _context(
            spot_ltp=99.7,
            vwap=100.0,
            ce_premium_change=1.0,
            pe_premium_change=13.0,
            regime_hint="TREND_DOWN",
        )
    )[0]

    assert candidate.direction == Direction.BUY_PUT
    assert candidate.raw_score > 0.0
    assert candidate.evidence["reclaim_direction"] == "BUY_PUT"


def test_vwap_reclaim_not_triggered_returns_diagnostic_candidate():
    candidate = vwap_reclaim_provider(
        _context(
            spot_ltp=103.0,
            vwap=100.0,
            ce_premium_change=2.0,
            pe_premium_change=2.0,
        )
    )[0]

    assert "VWAP_RECLAIM_NOT_TRIGGERED" in candidate.blockers
    assert candidate.raw_score == 0.0
    assert validate_strategy_candidate(candidate).valid is True


def test_failed_breakout_trap_provider_returns_valid_buy_put_candidate():
    candidate = failed_breakout_trap_provider(
        _context(
            spot_ltp=101.95,
            day_high=102.0,
            ce_premium_change=-1.0,
            pe_premium_change=12.0,
            regime_hint="TRAP_RISK",
        )
    )[0]
    result = validate_strategy_candidate(candidate)

    assert candidate.strategy_id == "FAILED_BREAKOUT_TRAP"
    assert candidate.movement_type == "FAILED_BREAKOUT_TRAP"
    assert candidate.direction == Direction.BUY_PUT
    assert candidate.status == CandidateStatus.RAW_CANDIDATE
    assert candidate.raw_score > 0.0
    assert candidate.blockers == ()
    assert candidate.evidence["provider"] == "FAILED_BREAKOUT_TRAP"
    assert candidate.evidence["trap_direction"] == "BUY_PUT"
    assert candidate.is_order_action is False
    assert result.valid is True


def test_failed_breakout_trap_provider_detects_lower_failure_buy_call_candidate():
    candidate = failed_breakout_trap_provider(
        _context(
            spot_ltp=98.05,
            day_low=98.0,
            ce_premium_change=13.0,
            pe_premium_change=-1.0,
            regime_hint="TRAP_RISK",
        )
    )[0]

    assert candidate.direction == Direction.BUY_CALL
    assert candidate.raw_score > 0.0
    assert candidate.evidence["trap_direction"] == "BUY_CALL"


def test_failed_breakout_trap_not_triggered_returns_diagnostic_candidate():
    candidate = failed_breakout_trap_provider(
        _context(
            spot_ltp=100.2,
            ce_premium_change=3.0,
            pe_premium_change=3.0,
            regime_hint="RANGE",
        )
    )[0]

    assert "FAILED_BREAKOUT_TRAP_NOT_TRIGGERED" in candidate.blockers
    assert candidate.raw_score == 0.0
    assert validate_strategy_candidate(candidate).valid is True


def test_vwap_trap_providers_register_through_registry():
    registry = register_vwap_trap_providers(MovementStrategyRegistry())
    result = registry.run(_context())

    assert registry.strategy_ids == ("VWAP_RECLAIM", "FAILED_BREAKOUT_TRAP")
    assert result.provider_count == 2
    assert len(result.candidates) == 2
    assert {candidate.strategy_id for candidate in result.candidates} == {"VWAP_RECLAIM", "FAILED_BREAKOUT_TRAP"}
    assert result.is_order_action is False


def test_vwap_trap_candidate_pool_blocks_wide_spread():
    result = build_vwap_trap_candidate_pool(_context(ce_spread_pct=4.0))
    vwap = next(candidate for candidate in result.candidates if candidate.strategy_id == "VWAP_RECLAIM")

    assert vwap.status == CandidateStatus.BLOCKED_CANDIDATE
    assert "WIDE_SPREAD" in vwap.blockers
    assert vwap.evidence["pool_hard_blockers"] == ["WIDE_SPREAD"]
    assert result.summary.blocked_count >= 1
    assert result.is_order_action is False


def test_vwap_trap_candidate_pool_blocks_fallback_quote():
    result = build_vwap_trap_candidate_pool(_context(quote_source="FALLBACK"))

    assert all(candidate.status == CandidateStatus.BLOCKED_CANDIDATE for candidate in result.candidates)
    assert all("FALLBACK_QUOTE_ONLY" in candidate.blockers for candidate in result.candidates)
    assert result.summary.valid_count == 0


def test_candidate_pool_preserves_vwap_trap_evidence():
    result = build_vwap_trap_candidate_pool(_context())
    vwap = next(candidate for candidate in result.candidates if candidate.strategy_id == "VWAP_RECLAIM")

    assert vwap.evidence["provider"] == "VWAP_RECLAIM"
    assert vwap.evidence["spot_ltp"] == 100.4
    assert vwap.evidence["vwap"] == 100.0
    assert vwap.evidence["day_high"] == 102.0
    assert vwap.evidence["ce_depth"] == 550.0


def test_chop_regime_hard_blocks_vwap_trap_pool():
    result = build_vwap_trap_candidate_pool(_context(regime_hint="CHOP"))

    assert all(candidate.status == CandidateStatus.BLOCKED_CANDIDATE for candidate in result.candidates)
    assert all("NO_TRADE_CHOP" in candidate.blockers for candidate in result.candidates)
    assert result.summary.blocked_count == 2
    assert result.summary.valid_count == 0


def test_all_vwap_trap_outputs_remain_non_order_actions():
    result = build_vwap_trap_candidate_pool(_context())
    payload = result.to_dict()

    assert payload["is_order_action"] is False
    assert payload["summary"]["is_order_action"] is False
    assert all(candidate["is_order_action"] is False for candidate in payload["candidates"])


def test_vwap_trap_providers_do_not_import_broker_order_api_or_dashboard_modules():
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

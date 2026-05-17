from __future__ import annotations

import ast
import inspect

import movement_engine.providers.opening_drive_orb as provider_module
from movement_engine import (
    CandidateStatus,
    Direction,
    MovementStrategyRegistry,
    StrategyContext,
    build_opening_drive_orb_candidate_pool,
    opening_drive_provider,
    orb_retest_provider,
    register_opening_drive_orb_providers,
    validate_strategy_candidate,
)


def _context(**overrides) -> StrategyContext:
    payload = {
        "symbol": "NIFTY",
        "ts_epoch": 12345.0,
        "spot_ltp": 101.4,
        "vwap": 100.2,
        "orb_high": 101.0,
        "orb_low": 99.4,
        "atr": 1.2,
        "atr_short": 1.4,
        "atr_long": 1.0,
        "volume_z": 2.2,
        "volatility_state": "VOLATILITY_EXPANSION",
        "regime_hint": "TREND_UP",
        "option_ce_ltp": 120.0,
        "option_pe_ltp": 95.0,
        "ce_premium_change": 18.0,
        "pe_premium_change": -8.0,
        "ce_spread_pct": 1.0,
        "pe_spread_pct": 1.2,
        "ce_depth": 500.0,
        "pe_depth": 450.0,
        "option_ltp_age_sec": 1.0,
        "quote_source": "PRIMARY",
        "time_of_day": "OPEN",
        "minutes_since_open": 12,
    }
    payload.update(overrides)
    return StrategyContext(**payload)


def test_opening_drive_provider_returns_valid_raw_buy_call_candidate():
    candidate = opening_drive_provider(_context())[0]
    result = validate_strategy_candidate(candidate)

    assert candidate.strategy_id == "OPENING_DRIVE"
    assert candidate.movement_type == "OPENING_MOMENTUM_EXPANSION"
    assert candidate.direction == Direction.BUY_CALL
    assert candidate.status == CandidateStatus.RAW_CANDIDATE
    assert candidate.raw_score > 0.0
    assert candidate.blockers == ()
    assert candidate.evidence["provider"] == "OPENING_DRIVE"
    assert candidate.evidence["is_order_action"] is False
    assert candidate.is_order_action is False
    assert result.valid is True


def test_opening_drive_provider_detects_downside_breakout():
    candidate = opening_drive_provider(
        _context(
            spot_ltp=98.8,
            vwap=100.0,
            ce_premium_change=-6.0,
            pe_premium_change=20.0,
            regime_hint="TREND_DOWN",
        )
    )[0]

    assert candidate.direction == Direction.BUY_PUT
    assert candidate.raw_score > 0.0
    assert candidate.evidence["breakout_direction"] == "BUY_PUT"


def test_opening_drive_not_triggered_returns_blocked_candidate_proposal():
    candidate = opening_drive_provider(_context(spot_ltp=100.2, volume_z=0.2))[0]

    assert "OPENING_DRIVE_NOT_TRIGGERED" in candidate.blockers
    assert candidate.raw_score == 0.0
    assert validate_strategy_candidate(candidate).valid is True


def test_orb_retest_provider_returns_valid_raw_buy_call_candidate():
    candidate = orb_retest_provider(_context(spot_ltp=101.08, volume_z=0.5))[0]
    result = validate_strategy_candidate(candidate)

    assert candidate.strategy_id == "ORB_RETEST"
    assert candidate.movement_type == "ORB_BREAKOUT_RETEST"
    assert candidate.direction == Direction.BUY_CALL
    assert candidate.status == CandidateStatus.RAW_CANDIDATE
    assert candidate.raw_score > 0.0
    assert candidate.blockers == ()
    assert candidate.evidence["provider"] == "ORB_RETEST"
    assert candidate.is_order_action is False
    assert result.valid is True


def test_orb_retest_provider_detects_downside_retest():
    candidate = orb_retest_provider(
        _context(
            spot_ltp=99.35,
            vwap=100.0,
            ce_premium_change=-5.0,
            pe_premium_change=15.0,
            regime_hint="TREND_DOWN",
        )
    )[0]

    assert candidate.direction == Direction.BUY_PUT
    assert candidate.evidence["retest_direction"] == "BUY_PUT"
    assert candidate.raw_score > 0.0


def test_providers_register_through_movement_registry():
    registry = register_opening_drive_orb_providers(MovementStrategyRegistry())
    result = registry.run(_context())

    assert registry.strategy_ids == ("OPENING_DRIVE", "ORB_RETEST")
    assert result.provider_count == 2
    assert len(result.candidates) == 2
    assert {candidate.strategy_id for candidate in result.candidates} == {"OPENING_DRIVE", "ORB_RETEST"}
    assert result.is_order_action is False


def test_opening_drive_orb_candidate_pool_blocks_wide_spread():
    result = build_opening_drive_orb_candidate_pool(_context(ce_spread_pct=4.5))
    opening_drive = next(candidate for candidate in result.candidates if candidate.strategy_id == "OPENING_DRIVE")

    assert opening_drive.status == CandidateStatus.BLOCKED_CANDIDATE
    assert "WIDE_SPREAD" in opening_drive.blockers
    assert opening_drive.evidence["pool_hard_blockers"] == ["WIDE_SPREAD"]
    assert result.summary.blocked_count >= 1
    assert result.is_order_action is False


def test_opening_drive_orb_candidate_pool_blocks_missing_depth():
    result = build_opening_drive_orb_candidate_pool(_context(ce_depth=0.0))
    opening_drive = next(candidate for candidate in result.candidates if candidate.strategy_id == "OPENING_DRIVE")

    assert opening_drive.status == CandidateStatus.BLOCKED_CANDIDATE
    assert "MISSING_DEPTH" in opening_drive.blockers
    assert opening_drive.evidence["pool_blocked"] is True


def test_candidate_pool_preserves_provider_evidence():
    result = build_opening_drive_orb_candidate_pool(_context())
    opening_drive = next(candidate for candidate in result.candidates if candidate.strategy_id == "OPENING_DRIVE")

    assert opening_drive.evidence["provider"] == "OPENING_DRIVE"
    assert opening_drive.evidence["orb_high"] == 101.0
    assert opening_drive.evidence["orb_low"] == 99.4
    assert opening_drive.evidence["ce_spread_pct"] == 1.0
    assert opening_drive.evidence["ce_depth"] == 500.0


def test_chop_regime_hard_blocks_through_pool():
    result = build_opening_drive_orb_candidate_pool(_context(regime_hint="CHOP"))

    assert all(candidate.status == CandidateStatus.BLOCKED_CANDIDATE for candidate in result.candidates)
    assert all("NO_TRADE_CHOP" in candidate.blockers for candidate in result.candidates)
    assert result.summary.blocked_count == 2
    assert result.summary.valid_count == 0


def test_all_provider_and_pool_outputs_remain_non_order_actions():
    result = build_opening_drive_orb_candidate_pool(_context())
    payload = result.to_dict()

    assert payload["is_order_action"] is False
    assert payload["summary"]["is_order_action"] is False
    assert all(candidate["is_order_action"] is False for candidate in payload["candidates"])


def test_opening_drive_orb_providers_do_not_import_broker_order_api_or_dashboard_modules():
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

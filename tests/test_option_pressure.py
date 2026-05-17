from __future__ import annotations

import ast
import inspect

import movement_engine.option_pressure as option_pressure_module
from movement_engine import (
    CandidateStatus,
    Direction,
    OPTION_PRESSURE_EVIDENCE_KEY,
    OptionPressureStatus,
    StrategyCandidate,
    StrategyContext,
    attach_option_pressure_confirmation,
    attach_option_pressure_to_candidates,
    build_candidate_pool,
    confirm_option_pressure,
    validate_strategy_candidate,
)


def _context(**overrides) -> StrategyContext:
    payload = {
        "symbol": "NIFTY",
        "ts_epoch": 44444.0,
        "option_ce_ltp": 120.0,
        "option_pe_ltp": 90.0,
        "ce_premium_change": 18.0,
        "pe_premium_change": -4.0,
        "ce_spread_pct": 0.8,
        "pe_spread_pct": 1.2,
        "ce_depth": 600.0,
        "pe_depth": 450.0,
        "option_ltp_age_sec": 1.0,
        "quote_source": "PRIMARY",
    }
    payload.update(overrides)
    return StrategyContext(**payload)


def _candidate(**overrides) -> StrategyCandidate:
    payload = {
        "schema_version": 1,
        "candidate_id": "move-1",
        "strategy_id": "TEST_PROVIDER",
        "movement_type": "TEST_MOVEMENT",
        "symbol": "NIFTY",
        "direction": Direction.BUY_CALL,
        "status": CandidateStatus.RAW_CANDIDATE,
        "raw_score": 0.70,
        "confidence_score": 0.65,
        "price_structure_score": 0.70,
        "option_confirmation_score": 0.40,
        "liquidity_score": 0.90,
        "freshness_score": 0.90,
        "volatility_score": 0.50,
        "regime_alignment_score": 0.60,
        "entry_trigger": "test trigger",
        "invalid_if": "test invalidation",
        "rank_reason": "test reason",
        "blockers": (),
        "warnings": (),
        "evidence": {"provider": "TEST_PROVIDER"},
    }
    payload.update(overrides)
    return StrategyCandidate(**payload)


def test_buy_call_option_pressure_confirms_ce_pressure():
    result = confirm_option_pressure(_context(), Direction.BUY_CALL)

    assert result.status == OptionPressureStatus.CONFIRMED
    assert result.confirmed is True
    assert result.pressure_score >= 0.62
    assert result.ce_pressure_score > result.pe_pressure_score
    assert result.premium_bias > 0
    assert result.blockers == ()
    assert result.is_order_action is False
    assert result.to_dict()["is_order_action"] is False


def test_buy_put_option_pressure_confirms_pe_pressure():
    result = confirm_option_pressure(
        _context(
            option_ce_ltp=95.0,
            option_pe_ltp=125.0,
            ce_premium_change=-5.0,
            pe_premium_change=20.0,
            ce_spread_pct=1.2,
            pe_spread_pct=0.7,
            ce_depth=300.0,
            pe_depth=650.0,
        ),
        Direction.BUY_PUT,
    )

    assert result.status == OptionPressureStatus.CONFIRMED
    assert result.confirmed is True
    assert result.pe_pressure_score > result.ce_pressure_score
    assert result.premium_bias < 0
    assert result.blockers == ()


def test_conflicting_option_pressure_blocks_candidate_direction():
    result = confirm_option_pressure(
        _context(ce_premium_change=-4.0, pe_premium_change=18.0),
        Direction.BUY_CALL,
    )

    assert result.status == OptionPressureStatus.CONFLICTING_PRESSURE
    assert "CONFLICTING_OPTION_PRESSURE" in result.blockers
    assert result.confirmed is False


def test_weak_option_confirmation_is_warning_not_hard_blocker():
    result = confirm_option_pressure(
        _context(ce_premium_change=4.0, pe_premium_change=1.0, ce_depth=150.0, ce_spread_pct=2.0),
        Direction.BUY_CALL,
    )

    assert result.status == OptionPressureStatus.WEAK_CONFIRMATION
    assert "WEAK_OPTION_CONFIRMATION" in result.warnings
    assert result.blockers == ()
    assert result.confirmed is False


def test_stale_option_ltp_blocks_confirmation():
    result = confirm_option_pressure(_context(option_ltp_age_sec=8.0), Direction.BUY_CALL)

    assert result.status == OptionPressureStatus.BLOCKED
    assert "STALE_OPTION_LTP" in result.blockers
    assert result.pressure_score > 0.0
    assert result.confirmed is False


def test_fallback_quote_blocks_confirmation():
    result = confirm_option_pressure(_context(quote_source="FALLBACK"), Direction.BUY_CALL)

    assert result.status == OptionPressureStatus.BLOCKED
    assert "FALLBACK_QUOTE_ONLY" in result.blockers
    assert result.confirmed is False


def test_wide_spread_and_missing_depth_block_directional_confirmation():
    result = confirm_option_pressure(_context(ce_spread_pct=4.5, ce_depth=0.0), Direction.BUY_CALL)

    assert result.status == OptionPressureStatus.BLOCKED
    assert "WIDE_SPREAD" in result.blockers
    assert "MISSING_DEPTH" in result.blockers
    assert result.spread_quality_score == 0.0
    assert result.depth_quality_score == 0.0


def test_no_trade_direction_is_not_applicable_not_order_action():
    result = confirm_option_pressure(_context(), Direction.NO_TRADE)

    assert result.status == OptionPressureStatus.NOT_APPLICABLE
    assert "OPTION_PRESSURE_NOT_APPLICABLE_FOR_NO_TRADE" in result.warnings
    assert result.pressure_score == 0.0
    assert result.is_order_action is False


def test_attach_option_pressure_confirmation_preserves_candidate_and_adds_evidence():
    candidate = _candidate()

    enriched = attach_option_pressure_confirmation(candidate, _context())
    validation = validate_strategy_candidate(enriched)

    assert enriched.candidate_id == candidate.candidate_id
    assert enriched.status == CandidateStatus.RAW_CANDIDATE
    assert enriched.option_confirmation_score >= 0.62
    assert OPTION_PRESSURE_EVIDENCE_KEY in enriched.evidence
    assert enriched.evidence[OPTION_PRESSURE_EVIDENCE_KEY]["status"] == "CONFIRMED"
    assert enriched.evidence["provider"] == "TEST_PROVIDER"
    assert enriched.is_order_action is False
    assert validation.valid is True


def test_attach_conflicting_option_pressure_adds_pool_hard_blocker():
    candidate = _candidate(direction=Direction.BUY_CALL)
    enriched = attach_option_pressure_confirmation(
        candidate,
        _context(ce_premium_change=-5.0, pe_premium_change=18.0),
    )
    pooled = build_candidate_pool([enriched])

    assert "CONFLICTING_OPTION_PRESSURE" in enriched.blockers
    assert "CONFLICTING_TRAP_SIGNAL" in enriched.blockers
    assert pooled.candidates[0].status == CandidateStatus.BLOCKED_CANDIDATE
    assert "CONFLICTING_TRAP_SIGNAL" in pooled.candidates[0].blockers
    assert pooled.summary.blocked_count == 1


def test_attach_weak_confirmation_keeps_candidate_raw_with_warning():
    candidate = _candidate(direction=Direction.BUY_CALL)
    enriched = attach_option_pressure_confirmation(
        candidate,
        _context(ce_premium_change=4.0, pe_premium_change=1.0, ce_depth=150.0, ce_spread_pct=2.0),
    )

    assert enriched.status == CandidateStatus.RAW_CANDIDATE
    assert "WEAK_OPTION_CONFIRMATION" in enriched.warnings
    assert enriched.evidence[OPTION_PRESSURE_EVIDENCE_KEY]["status"] == "WEAK_CONFIRMATION"
    assert validate_strategy_candidate(enriched).valid is True


def test_attach_option_pressure_to_candidates_returns_tuple():
    candidates = [_candidate(candidate_id="one"), _candidate(candidate_id="two")]

    enriched = attach_option_pressure_to_candidates(candidates, _context())

    assert isinstance(enriched, tuple)
    assert [candidate.candidate_id for candidate in enriched] == ["one", "two"]
    assert all(OPTION_PRESSURE_EVIDENCE_KEY in candidate.evidence for candidate in enriched)
    assert all(candidate.is_order_action is False for candidate in enriched)


def test_option_pressure_module_does_not_import_broker_order_api_or_dashboard_modules():
    forbidden_import_roots = {
        "api",
        "broker_contract",
        "dashboard",
        "order_intent",
        "paper_broker",
    }

    tree = ast.parse(inspect.getsource(option_pressure_module))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint(forbidden_import_roots)

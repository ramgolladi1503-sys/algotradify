from __future__ import annotations

import ast
import inspect

import movement_engine.no_trade_filter as no_trade_filter_module
from movement_engine import (
    CandidateStatus,
    Direction,
    NO_TRADE_FILTER_EVIDENCE_KEY,
    OPTION_PRESSURE_EVIDENCE_KEY,
    NoTradeDecision,
    StrategyCandidate,
    StrategyContext,
    apply_no_trade_filter,
    apply_no_trade_filter_to_candidates,
    attach_option_pressure_confirmation,
    build_candidate_pool,
    validate_strategy_candidate,
)


def _context(**overrides) -> StrategyContext:
    payload = {
        "symbol": "NIFTY",
        "ts_epoch": 55555.0,
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
        "candidate_id": "candidate-1",
        "strategy_id": "TEST_PROVIDER",
        "movement_type": "TEST_MOVEMENT",
        "symbol": "NIFTY",
        "direction": Direction.BUY_CALL,
        "status": CandidateStatus.RAW_CANDIDATE,
        "raw_score": 0.70,
        "confidence_score": 0.65,
        "price_structure_score": 0.70,
        "option_confirmation_score": 0.65,
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


def _enriched_candidate(candidate: StrategyCandidate | None = None, **context_overrides) -> StrategyCandidate:
    return attach_option_pressure_confirmation(candidate or _candidate(), _context(**context_overrides))


def test_clean_confirmed_candidate_is_allowed():
    candidate = _enriched_candidate()

    filtered, result = apply_no_trade_filter(candidate)

    assert result.decision == NoTradeDecision.ALLOW_CANDIDATE
    assert filtered.status == CandidateStatus.RAW_CANDIDATE
    assert filtered.direction == Direction.BUY_CALL
    assert filtered.blockers == ()
    assert filtered.evidence[NO_TRADE_FILTER_EVIDENCE_KEY]["decision"] == "ALLOW_CANDIDATE"
    assert filtered.evidence[OPTION_PRESSURE_EVIDENCE_KEY]["status"] == "CONFIRMED"
    assert filtered.is_order_action is False
    assert validate_strategy_candidate(filtered).valid is True


def test_conflicting_option_pressure_blocks_candidate():
    candidate = _enriched_candidate(ce_premium_change=-5.0, pe_premium_change=18.0)

    filtered, result = apply_no_trade_filter(candidate)

    assert result.decision == NoTradeDecision.BLOCK_CANDIDATE
    assert filtered.status == CandidateStatus.BLOCKED_CANDIDATE
    assert "CONFLICTING_OPTION_PRESSURE" in filtered.blockers
    assert "CONFLICTING_TRAP_SIGNAL" in filtered.blockers
    assert filtered.evidence[NO_TRADE_FILTER_EVIDENCE_KEY]["decision"] == "BLOCK_CANDIDATE"
    assert validate_strategy_candidate(filtered).valid is True


def test_hard_blocker_blocks_candidate():
    candidate = _enriched_candidate(_candidate(blockers=("MARKET_CLOSED",)))

    filtered, result = apply_no_trade_filter(candidate)

    assert result.decision == NoTradeDecision.BLOCK_CANDIDATE
    assert filtered.status == CandidateStatus.BLOCKED_CANDIDATE
    assert "MARKET_CLOSED" in filtered.blockers
    assert result.diagnostics[0]["code"] == "HARD_NO_TRADE_BLOCKER"


def test_option_pressure_blocked_blocks_candidate():
    candidate = _enriched_candidate(option_ltp_age_sec=9.0)

    filtered, result = apply_no_trade_filter(candidate)

    assert result.decision == NoTradeDecision.BLOCK_CANDIDATE
    assert filtered.status == CandidateStatus.BLOCKED_CANDIDATE
    assert "STALE_OPTION_LTP" in filtered.blockers
    assert "OPTION_PRESSURE_BLOCKED" in filtered.blockers


def test_weak_confirmation_with_bad_liquidity_blocks_candidate():
    candidate = _enriched_candidate(
        _candidate(liquidity_score=0.30),
        ce_premium_change=4.0,
        pe_premium_change=1.0,
        ce_depth=150.0,
        ce_spread_pct=2.0,
    )

    filtered, result = apply_no_trade_filter(candidate)

    assert result.decision == NoTradeDecision.BLOCK_CANDIDATE
    assert filtered.status == CandidateStatus.BLOCKED_CANDIDATE
    assert "WEAK_CONFIRMATION_WITH_RISK_CONTEXT" in filtered.blockers
    assert filtered.evidence[OPTION_PRESSURE_EVIDENCE_KEY]["status"] == "WEAK_CONFIRMATION"


def test_weak_confirmation_without_bad_context_is_allowed_with_warning():
    candidate = _enriched_candidate(
        ce_premium_change=4.0,
        pe_premium_change=1.0,
        ce_depth=600.0,
        ce_spread_pct=0.8,
    )

    filtered, result = apply_no_trade_filter(candidate)

    assert result.decision == NoTradeDecision.ALLOW_CANDIDATE
    assert filtered.status == CandidateStatus.RAW_CANDIDATE
    assert "WEAK_OPTION_CONFIRMATION_ALLOWED" in filtered.warnings
    assert filtered.evidence[NO_TRADE_FILTER_EVIDENCE_KEY]["decision"] == "ALLOW_CANDIDATE"


def test_no_trade_direction_converts_to_no_trade_candidate():
    candidate = _candidate(
        direction=Direction.NO_TRADE,
        status=CandidateStatus.RAW_CANDIDATE,
        option_confirmation_score=0.0,
    )

    filtered, result = apply_no_trade_filter(candidate)

    assert result.decision == NoTradeDecision.NO_TRADE
    assert filtered.status == CandidateStatus.NO_TRADE
    assert filtered.direction == Direction.NO_TRADE
    assert "NO_TRADE_DIRECTION" in filtered.blockers
    assert validate_strategy_candidate(filtered).valid is True


def test_no_trade_status_converts_to_no_trade_direction():
    candidate = _candidate(
        direction=Direction.NO_TRADE,
        status=CandidateStatus.NO_TRADE,
        blockers=("NO_TRADE_CHOP",),
        option_confirmation_score=0.0,
    )

    filtered, result = apply_no_trade_filter(candidate)

    assert result.decision == NoTradeDecision.NO_TRADE
    assert filtered.status == CandidateStatus.NO_TRADE
    assert filtered.direction == Direction.NO_TRADE
    assert "NO_TRADE_STATUS" in filtered.blockers
    assert "NO_TRADE_CHOP" in filtered.blockers


def test_batch_filter_returns_summary_counts():
    allowed = _enriched_candidate(_candidate(candidate_id="allowed"))
    blocked = _enriched_candidate(_candidate(candidate_id="blocked"), quote_source="FALLBACK")
    no_trade = _candidate(
        candidate_id="no-trade",
        direction=Direction.NO_TRADE,
        status=CandidateStatus.RAW_CANDIDATE,
        option_confirmation_score=0.0,
    )

    result = apply_no_trade_filter_to_candidates([allowed, blocked, no_trade])

    assert result.summary.input_count == 3
    assert result.summary.allowed_count == 1
    assert result.summary.blocked_count == 1
    assert result.summary.no_trade_count == 1
    assert result.is_order_action is False
    assert result.to_dict()["summary"]["is_order_action"] is False


def test_no_trade_filter_output_can_flow_to_candidate_pool():
    candidate = _enriched_candidate(ce_premium_change=-5.0, pe_premium_change=18.0)
    filtered, _ = apply_no_trade_filter(candidate)

    pooled = build_candidate_pool([filtered])

    assert pooled.candidates[0].status == CandidateStatus.BLOCKED_CANDIDATE
    assert "CONFLICTING_TRAP_SIGNAL" in pooled.candidates[0].blockers
    assert pooled.summary.blocked_count == 1
    assert pooled.is_order_action is False


def test_no_trade_filter_preserves_original_and_added_evidence():
    candidate = _enriched_candidate(_candidate(evidence={"provider": "TEST_PROVIDER", "custom": {"x": 1}}))

    filtered, result = apply_no_trade_filter(candidate)

    assert filtered.evidence["provider"] == "TEST_PROVIDER"
    assert filtered.evidence["custom"] == {"x": 1}
    assert OPTION_PRESSURE_EVIDENCE_KEY in filtered.evidence
    assert NO_TRADE_FILTER_EVIDENCE_KEY in filtered.evidence
    assert filtered.evidence[NO_TRADE_FILTER_EVIDENCE_KEY]["diagnostics"][0]["is_order_action"] is False
    assert result.is_order_action is False


def test_no_trade_filter_module_does_not_import_broker_order_api_or_dashboard_modules():
    forbidden_import_roots = {
        "api",
        "broker_contract",
        "dashboard",
        "order_intent",
        "paper_broker",
    }

    tree = ast.parse(inspect.getsource(no_trade_filter_module))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint(forbidden_import_roots)

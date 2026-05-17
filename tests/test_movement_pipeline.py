from __future__ import annotations

import ast
import inspect

import movement_engine.pipeline as pipeline_module
from movement_engine import (
    CandidateStatus,
    Direction,
    MovementStrategyRegistry,
    NO_TRADE_FILTER_EVIDENCE_KEY,
    OPTION_PRESSURE_EVIDENCE_KEY,
    RANKER_EVIDENCE_KEY,
    StrategyCandidate,
    StrategyContext,
    build_default_movement_registry,
    run_movement_opportunity_pipeline,
    validate_strategy_candidate,
)


def _context(**overrides) -> StrategyContext:
    payload = {
        "symbol": "NIFTY",
        "ts_epoch": 66666.0,
        "spot_ltp": 101.4,
        "vwap": 101.0,
        "orb_high": 101.0,
        "orb_low": 99.5,
        "day_high": 101.2,
        "day_low": 99.0,
        "prev_day_high": 102.0,
        "prev_day_low": 98.0,
        "atr": 1.1,
        "atr_short": 0.7,
        "atr_long": 1.0,
        "range_width_pct": 0.35,
        "volume_z": 1.9,
        "volatility_state": "COMPRESSION",
        "regime_hint": "COMPRESSION",
        "option_ce_ltp": 125.0,
        "option_pe_ltp": 85.0,
        "ce_premium_change": 22.0,
        "pe_premium_change": -4.0,
        "ce_spread_pct": 0.8,
        "pe_spread_pct": 1.1,
        "ce_depth": 650.0,
        "pe_depth": 500.0,
        "option_ltp_age_sec": 1.0,
        "quote_source": "PRIMARY",
        "time_of_day": "OPEN",
        "minutes_since_open": 14,
    }
    payload.update(overrides)
    return StrategyContext(**payload)


def _candidate(candidate_id: str = "pipe-1") -> StrategyCandidate:
    return StrategyCandidate(
        schema_version=1,
        candidate_id=candidate_id,
        strategy_id="PIPELINE_TEST_PROVIDER",
        movement_type="PIPELINE_TEST_MOVEMENT",
        symbol="NIFTY",
        direction=Direction.BUY_CALL,
        status=CandidateStatus.RAW_CANDIDATE,
        raw_score=0.75,
        confidence_score=0.70,
        price_structure_score=0.72,
        option_confirmation_score=0.65,
        liquidity_score=0.90,
        freshness_score=0.90,
        volatility_score=0.60,
        regime_alignment_score=0.65,
        entry_trigger="pipeline test trigger",
        invalid_if="pipeline test invalidation",
        rank_reason="pipeline test rank reason",
        evidence={"provider": "PIPELINE_TEST_PROVIDER"},
    )


def test_default_movement_registry_registers_all_default_providers():
    registry = build_default_movement_registry()

    assert registry.provider_count == 6
    assert registry.strategy_ids == (
        "OPENING_DRIVE",
        "ORB_RETEST",
        "COMPRESSION_BREAKOUT",
        "TREND_PULLBACK",
        "VWAP_RECLAIM",
        "FAILED_BREAKOUT_TRAP",
    )


def test_pipeline_runs_full_read_only_flow_with_default_registry():
    result = run_movement_opportunity_pipeline(_context())
    payload = result.to_dict()

    assert result.summary.provider_count == 6
    assert result.summary.registry_candidate_count == 6
    assert result.summary.pooled_candidate_count == 6
    assert result.summary.option_enriched_count == 6
    assert result.summary.ranked_count >= 1
    assert result.summary.top_candidate_id is not None
    assert result.summary.read_only is True
    assert result.is_order_action is False
    assert payload["is_order_action"] is False
    assert payload["summary"]["is_order_action"] is False
    assert payload["read_only"] is True


def test_pipeline_ranked_candidates_preserve_stage_evidence():
    result = run_movement_opportunity_pipeline(_context())
    ranked = result.rank_result.ranked_candidates[0]

    assert OPTION_PRESSURE_EVIDENCE_KEY in ranked.evidence
    assert NO_TRADE_FILTER_EVIDENCE_KEY in ranked.evidence
    assert RANKER_EVIDENCE_KEY in ranked.evidence
    assert ranked.evidence[RANKER_EVIDENCE_KEY]["rank"] == 1
    assert ranked.evidence[RANKER_EVIDENCE_KEY]["is_order_action"] is False
    assert validate_strategy_candidate(ranked).valid is True


def test_pipeline_blocks_all_candidates_on_fallback_quote():
    result = run_movement_opportunity_pipeline(_context(quote_source="FALLBACK"))

    assert result.summary.blocked_count == result.summary.option_enriched_count
    assert result.summary.ranked_count == 0
    assert result.rank_result.ranked_candidates == ()
    assert result.rank_result.summary.top_candidate_id is None
    assert all(candidate.status == CandidateStatus.BLOCKED_CANDIDATE for candidate in result.no_trade_filter_result.candidates)


def test_pipeline_with_empty_registry_is_safe():
    registry = MovementStrategyRegistry()

    result = run_movement_opportunity_pipeline(_context(), registry=registry)

    assert result.summary.provider_count == 0
    assert result.summary.registry_candidate_count == 0
    assert result.summary.pooled_candidate_count == 0
    assert result.summary.ranked_count == 0
    assert result.summary.top_candidate_id is None
    assert result.is_order_action is False


def test_pipeline_preserves_provider_exception_diagnostics():
    registry = MovementStrategyRegistry()

    def broken_provider(context):
        raise RuntimeError("provider failed")

    registry.register_provider("BROKEN_PROVIDER", broken_provider)

    result = run_movement_opportunity_pipeline(_context(), registry=registry)

    assert result.summary.provider_count == 1
    assert result.summary.registry_candidate_count == 0
    assert result.summary.diagnostic_count >= 1
    assert "PROVIDER_EXCEPTION:BROKEN_PROVIDER" in result.warnings
    assert any(diagnostic["code"] == "PROVIDER_EXCEPTION" for diagnostic in result.diagnostics)
    assert all(diagnostic["is_order_action"] is False for diagnostic in result.diagnostics)


def test_pipeline_accepts_custom_registry_candidate_and_ranks_it():
    registry = MovementStrategyRegistry()
    registry.register_provider("PIPELINE_TEST_PROVIDER", lambda context: [_candidate()])

    result = run_movement_opportunity_pipeline(_context(), registry=registry)

    assert result.summary.provider_count == 1
    assert result.summary.registry_candidate_count == 1
    assert result.summary.ranked_count == 1
    assert result.rank_result.ranked_candidates[0].candidate_id == "pipe-1"
    assert result.rank_result.ranked_candidates[0].status == CandidateStatus.RANKED_OPPORTUNITY


def test_pipeline_summary_counts_match_stage_outputs():
    result = run_movement_opportunity_pipeline(_context())

    assert result.summary.registry_candidate_count == len(result.registry_result.candidates)
    assert result.summary.pooled_candidate_count == len(result.candidate_pool_result.candidates)
    assert result.summary.option_enriched_count == len(result.option_enriched_candidates)
    assert result.summary.allowed_count == result.no_trade_filter_result.summary.allowed_count
    assert result.summary.blocked_count == result.no_trade_filter_result.summary.blocked_count
    assert result.summary.no_trade_count == result.no_trade_filter_result.summary.no_trade_count
    assert result.summary.ranked_count == result.rank_result.summary.ranked_count
    assert result.summary.excluded_count == result.rank_result.summary.excluded_count


def test_pipeline_module_does_not_import_broker_order_api_or_dashboard_modules():
    forbidden_import_roots = {
        "api",
        "broker_contract",
        "dashboard",
        "order_intent",
        "paper_broker",
    }

    tree = ast.parse(inspect.getsource(pipeline_module))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint(forbidden_import_roots)

from __future__ import annotations

import ast
import inspect

import movement_engine.ranker as ranker_module
from movement_engine import (
    CandidateStatus,
    Direction,
    NO_TRADE_FILTER_EVIDENCE_KEY,
    RANKER_EVIDENCE_KEY,
    RankExclusionReason,
    StrategyCandidate,
    build_candidate_pool,
    rank_movement_candidates,
    validate_strategy_candidate,
)


def _allowed_evidence(**extra):
    evidence = {
        "provider": "TEST_PROVIDER",
        NO_TRADE_FILTER_EVIDENCE_KEY: {
            "decision": "ALLOW_CANDIDATE",
            "is_order_action": False,
        },
    }
    evidence.update(extra)
    return evidence


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
        "evidence": _allowed_evidence(),
    }
    payload.update(overrides)
    return StrategyCandidate(**payload)


def test_empty_ranker_returns_stable_empty_result():
    result = rank_movement_candidates([])

    assert result.ranked_candidates == ()
    assert result.rank_records == ()
    assert result.exclusions == ()
    assert result.summary.input_count == 0
    assert result.summary.ranked_count == 0
    assert result.summary.excluded_count == 0
    assert result.summary.top_candidate_id is None
    assert result.is_order_action is False
    assert result.to_dict()["is_order_action"] is False


def test_ranker_ranks_allowed_candidates_by_weighted_score():
    weak = _candidate(candidate_id="weak", strategy_id="B", option_confirmation_score=0.40, liquidity_score=0.50)
    strong = _candidate(candidate_id="strong", strategy_id="A", option_confirmation_score=0.95, liquidity_score=0.95)

    result = rank_movement_candidates([weak, strong])

    assert [candidate.candidate_id for candidate in result.ranked_candidates] == ["strong", "weak"]
    assert [record.rank for record in result.rank_records] == [1, 2]
    assert result.rank_records[0].rank_score > result.rank_records[1].rank_score
    assert result.summary.top_candidate_id == "strong"
    assert result.summary.ranked_count == 2


def test_ranker_sets_ranked_opportunity_status_and_preserves_evidence():
    candidate = _candidate(evidence=_allowed_evidence(custom={"x": 1}))

    result = rank_movement_candidates([candidate])
    ranked = result.ranked_candidates[0]

    assert ranked.status == CandidateStatus.RANKED_OPPORTUNITY
    assert ranked.direction == Direction.BUY_CALL
    assert ranked.evidence["custom"] == {"x": 1}
    assert ranked.evidence[RANKER_EVIDENCE_KEY]["rank"] == 1
    assert ranked.evidence[RANKER_EVIDENCE_KEY]["is_order_action"] is False
    assert ranked.is_order_action is False
    assert validate_strategy_candidate(ranked).valid is True


def test_ranker_uses_deterministic_tie_breakers():
    alpha = _candidate(candidate_id="alpha", strategy_id="A")
    beta = _candidate(candidate_id="beta", strategy_id="B")

    result = rank_movement_candidates([beta, alpha])

    assert [candidate.candidate_id for candidate in result.ranked_candidates] == ["alpha", "beta"]
    assert result.rank_records[0].tie_breaker[-2:] == ("A", "alpha")


def test_ranker_excludes_blocked_candidates():
    candidate = _candidate(
        candidate_id="blocked",
        status=CandidateStatus.BLOCKED_CANDIDATE,
        blockers=("WIDE_SPREAD",),
    )

    result = rank_movement_candidates([candidate])

    assert result.ranked_candidates == ()
    assert result.exclusions[0].reason == RankExclusionReason.BLOCKED_CANDIDATE
    assert result.exclusions[0].blockers == ("WIDE_SPREAD",)
    assert result.summary.blocked_count == 1
    assert result.summary.excluded_count == 1
    assert "NO_RANKABLE_CANDIDATES" in result.warnings


def test_ranker_excludes_no_trade_candidates():
    candidate = _candidate(
        candidate_id="no-trade",
        direction=Direction.NO_TRADE,
        status=CandidateStatus.NO_TRADE,
        option_confirmation_score=0.0,
    )

    result = rank_movement_candidates([candidate])

    assert result.ranked_candidates == ()
    assert result.exclusions[0].reason == RankExclusionReason.NO_TRADE
    assert result.summary.no_trade_count == 1
    assert result.summary.excluded_count == 1


def test_ranker_excludes_candidate_without_allowed_no_trade_filter_evidence():
    candidate = _candidate(candidate_id="missing-filter", evidence={"provider": "TEST_PROVIDER"})

    result = rank_movement_candidates([candidate])

    assert result.ranked_candidates == ()
    assert result.exclusions[0].reason == RankExclusionReason.NOT_ALLOWED_BY_NO_TRADE_FILTER
    assert result.diagnostics[0]["code"] == "RANK_EXCLUDED"
    assert result.diagnostics[0]["is_order_action"] is False


def test_ranker_excludes_candidates_denied_by_no_trade_filter():
    candidate = _candidate(
        candidate_id="denied-filter",
        evidence={
            "provider": "TEST_PROVIDER",
            NO_TRADE_FILTER_EVIDENCE_KEY: {"decision": "BLOCK_CANDIDATE", "is_order_action": False},
        },
    )

    result = rank_movement_candidates([candidate])

    assert result.ranked_candidates == ()
    assert result.exclusions[0].reason == RankExclusionReason.NOT_ALLOWED_BY_NO_TRADE_FILTER


def test_ranker_result_can_flow_to_candidate_pool():
    candidate = _candidate(candidate_id="ranked")

    ranked = rank_movement_candidates([candidate]).ranked_candidates[0]
    pooled = build_candidate_pool([ranked])

    assert pooled.candidates[0].status == CandidateStatus.RANKED_OPPORTUNITY
    assert pooled.summary.valid_count == 1
    assert pooled.is_order_action is False


def test_ranker_all_outputs_are_non_order_actions():
    result = rank_movement_candidates([_candidate(candidate_id="one")])
    payload = result.to_dict()

    assert payload["is_order_action"] is False
    assert payload["summary"]["is_order_action"] is False
    assert payload["rank_records"][0]["is_order_action"] is False
    assert payload["ranked_candidates"][0]["is_order_action"] is False


def test_ranker_module_does_not_import_broker_order_api_or_dashboard_modules():
    forbidden_import_roots = {
        "api",
        "broker_contract",
        "dashboard",
        "order_intent",
        "paper_broker",
    }

    tree = ast.parse(inspect.getsource(ranker_module))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint(forbidden_import_roots)

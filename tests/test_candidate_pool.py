from __future__ import annotations

import ast
import inspect

import movement_engine.candidate_pool as candidate_pool_module
import movement_engine.registry as registry_module
from movement_engine import (
    CandidateStatus,
    Direction,
    StrategyCandidate,
    build_candidate_pool,
)


def _candidate(**overrides) -> StrategyCandidate:
    payload = {
        "schema_version": 1,
        "candidate_id": "move-1",
        "strategy_id": "TEST_PROVIDER",
        "movement_type": "TEST_MOVEMENT",
        "symbol": "NIFTY",
        "direction": Direction.BUY_CALL,
        "status": CandidateStatus.RAW_CANDIDATE,
        "raw_score": 0.65,
        "confidence_score": 0.60,
        "price_structure_score": 0.60,
        "option_confirmation_score": 0.50,
        "liquidity_score": 0.80,
        "freshness_score": 0.90,
        "volatility_score": 0.50,
        "regime_alignment_score": 0.60,
        "entry_trigger": "test trigger",
        "invalid_if": "test invalidation",
        "rank_reason": "test reason",
        "blockers": (),
        "warnings": (),
        "evidence": {"source": "unit-test"},
    }
    payload.update(overrides)
    return StrategyCandidate(**payload)


def test_empty_candidate_pool_returns_stable_empty_summary():
    result = build_candidate_pool([])

    assert result.candidates == ()
    assert result.summary.input_count == 0
    assert result.summary.candidate_count == 0
    assert result.summary.raw_count == 0
    assert result.summary.valid_count == 0
    assert result.summary.blocked_count == 0
    assert result.summary.no_trade_count == 0
    assert result.is_order_action is False
    assert result.summary.is_order_action is False


def test_candidate_pool_accepts_valid_provider_candidates():
    candidate = _candidate()
    result = build_candidate_pool([candidate])

    assert result.candidates == (candidate,)
    assert result.summary.input_count == 1
    assert result.summary.raw_count == 1
    assert result.candidates[0].to_dict()["is_order_action"] is False


def test_invalid_provider_mapping_is_blocked_and_diagnosed():
    payload = _candidate().to_dict()
    payload["symbol"] = ""

    result = build_candidate_pool([payload])

    assert len(result.candidates) == 1
    assert result.candidates[0].status == CandidateStatus.BLOCKED_CANDIDATE
    assert "SYMBOL_REQUIRED" in result.candidates[0].blockers
    assert result.diagnostics[0]["code"] == "INVALID_CANDIDATE_CONTRACT"
    assert result.summary.blocked_count == 1
    assert result.candidates[0].is_order_action is False


def test_non_candidate_provider_output_is_blocked_and_diagnosed():
    result = build_candidate_pool(["bad-output"])

    assert len(result.candidates) == 1
    assert result.candidates[0].status == CandidateStatus.BLOCKED_CANDIDATE
    assert "INVALID_PROVIDER_OUTPUT" in result.candidates[0].blockers
    assert result.diagnostics[0]["code"] == "INVALID_PROVIDER_OUTPUT"
    assert result.summary.blocked_count == 1


def test_duplicate_candidates_are_deduped_deterministically():
    weak = _candidate(candidate_id="dup-1", strategy_id="A", raw_score=0.30)
    strong = _candidate(candidate_id="dup-1", strategy_id="B", raw_score=0.90)

    result = build_candidate_pool([weak, strong])

    assert len(result.candidates) == 1
    assert result.candidates[0].strategy_id == "B"
    assert result.candidates[0].raw_score == 0.90
    assert "DUPLICATE_CANDIDATE_DEDUPED" in result.warnings
    assert result.diagnostics[0]["code"] == "DUPLICATE_CANDIDATE_DEDUPED"


def test_hard_blockers_prevent_validated_or_ranked_status():
    candidate = _candidate(
        status=CandidateStatus.VALIDATED_CANDIDATE,
        blockers=("WIDE_SPREAD",),
        evidence={"spread_pct": 2.5},
    )

    result = build_candidate_pool([candidate])
    blocked = result.candidates[0]

    assert blocked.status == CandidateStatus.BLOCKED_CANDIDATE
    assert "WIDE_SPREAD" in blocked.blockers
    assert blocked.evidence["spread_pct"] == 2.5
    assert blocked.evidence["pool_hard_blockers"] == ["WIDE_SPREAD"]
    assert blocked.evidence["pool_blocked"] is True
    assert "POOL_HARD_BLOCKER_APPLIED" in blocked.warnings
    assert result.summary.blocked_count == 1
    assert result.summary.valid_count == 0


def test_no_trade_hard_blocker_stays_no_trade_when_direction_is_no_trade():
    candidate = _candidate(
        candidate_id="no-trade-1",
        direction=Direction.NO_TRADE,
        status=CandidateStatus.NO_TRADE,
        blockers=("NO_TRADE_CHOP",),
    )

    result = build_candidate_pool([candidate])

    assert result.candidates[0].status == CandidateStatus.NO_TRADE
    assert result.summary.no_trade_count == 1
    assert result.summary.blocked_count == 0


def test_candidate_pool_summary_includes_raw_valid_blocked_and_no_trade_counts():
    raw = _candidate(candidate_id="raw", status=CandidateStatus.RAW_CANDIDATE)
    valid = _candidate(candidate_id="valid", status=CandidateStatus.VALIDATED_CANDIDATE)
    blocked = _candidate(candidate_id="blocked", status=CandidateStatus.BLOCKED_CANDIDATE, blockers=("MISSING_DEPTH",))
    no_trade = _candidate(
        candidate_id="no-trade",
        direction=Direction.NO_TRADE,
        status=CandidateStatus.NO_TRADE,
        blockers=("NO_TRADE_CHOP",),
    )

    result = build_candidate_pool([raw, valid, blocked, no_trade])
    summary = result.summary.to_dict()

    assert summary["input_count"] == 4
    assert summary["candidate_count"] == 4
    assert summary["raw_count"] == 1
    assert summary["valid_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["no_trade_count"] == 1
    assert summary["is_order_action"] is False


def test_candidate_evidence_is_preserved():
    candidate = _candidate(evidence={"vwap_alignment": "bullish", "nested": {"x": 1}})

    result = build_candidate_pool([candidate])

    assert result.candidates[0].evidence["vwap_alignment"] == "bullish"
    assert result.candidates[0].evidence["nested"] == {"x": 1}


def test_candidate_pool_preserves_upstream_registry_diagnostics():
    result = build_candidate_pool(
        [],
        upstream_warnings=["PROVIDER_EXCEPTION:BROKEN"],
        upstream_diagnostics=[{"code": "PROVIDER_EXCEPTION", "is_order_action": False}],
    )

    assert "PROVIDER_EXCEPTION:BROKEN" in result.warnings
    assert result.diagnostics[0]["code"] == "PROVIDER_EXCEPTION"
    assert result.diagnostics[0]["is_order_action"] is False


def test_all_candidate_pool_outputs_remain_non_order_actions():
    result = build_candidate_pool([_candidate(status=CandidateStatus.VALIDATED_CANDIDATE)])

    payload = result.to_dict()

    assert payload["is_order_action"] is False
    assert payload["summary"]["is_order_action"] is False
    assert payload["candidates"][0]["is_order_action"] is False


def test_movement_registry_and_candidate_pool_do_not_import_broker_or_order_modules():
    forbidden_import_roots = {
        "broker_contract",
        "paper_broker",
        "order_intent",
    }

    for module in (registry_module, candidate_pool_module):
        tree = ast.parse(inspect.getsource(module))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])

        assert imported_roots.isdisjoint(forbidden_import_roots)

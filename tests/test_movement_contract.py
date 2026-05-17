from __future__ import annotations

from movement_engine import (
    CandidateStatus,
    Direction,
    StrategyCandidate,
    StrategyContext,
    candidate_from_mapping,
    validate_strategy_candidate,
)


def _candidate(**overrides):
    payload = {
        "schema_version": 1,
        "candidate_id": "move-1",
        "strategy_id": "OPENING_DRIVE",
        "movement_type": "MOMENTUM_EXPANSION",
        "symbol": "NIFTY",
        "direction": Direction.BUY_CALL,
        "status": CandidateStatus.RAW_CANDIDATE,
        "raw_score": 0.72,
        "confidence_score": 0.70,
        "price_structure_score": 0.75,
        "option_confirmation_score": 0.68,
        "liquidity_score": 0.80,
        "freshness_score": 0.90,
        "volatility_score": 0.60,
        "regime_alignment_score": 0.65,
        "entry_trigger": "opening high break",
        "invalid_if": "price returns below opening range",
        "rank_reason": "opening drive with premium confirmation",
        "blockers": (),
        "warnings": (),
        "evidence": {"vwap_alignment": "bullish"},
    }
    payload.update(overrides)
    return StrategyCandidate(**payload)


def test_valid_strategy_candidate_serializes_and_validates():
    candidate = _candidate()

    result = validate_strategy_candidate(candidate)
    payload = candidate.to_dict()

    assert result.valid is True
    assert result.blockers == []
    assert result.is_order_action is False
    assert payload["direction"] == "BUY_CALL"
    assert payload["status"] == "RAW_CANDIDATE"
    assert payload["is_order_action"] is False
    assert payload["evidence"]["vwap_alignment"] == "bullish"


def test_candidate_from_mapping_round_trips_valid_payload():
    original = _candidate().to_dict()
    rebuilt = candidate_from_mapping(original)

    assert rebuilt == _candidate()
    assert validate_strategy_candidate(rebuilt).valid is True


def test_invalid_direction_fails_validation():
    payload = _candidate().to_dict()
    payload["direction"] = "BUY_STOCK"

    result = validate_strategy_candidate(payload)

    assert result.valid is False
    assert "INVALID_DIRECTION" in result.blockers


def test_invalid_status_fails_validation():
    payload = _candidate().to_dict()
    payload["status"] = "EXECUTE_NOW"

    result = validate_strategy_candidate(payload)

    assert result.valid is False
    assert "INVALID_STATUS" in result.blockers


def test_score_outside_zero_to_one_fails_validation():
    payload = _candidate().to_dict()
    payload["raw_score"] = 1.5
    payload["freshness_score"] = -0.1

    result = validate_strategy_candidate(payload)

    assert result.valid is False
    assert "RAW_SCORE_OUT_OF_RANGE" in result.blockers
    assert "FRESHNESS_SCORE_OUT_OF_RANGE" in result.blockers


def test_missing_required_identity_fields_fail_validation():
    payload = _candidate().to_dict()
    payload["candidate_id"] = ""
    payload["strategy_id"] = ""
    payload["symbol"] = ""

    result = validate_strategy_candidate(payload)

    assert result.valid is False
    assert "CANDIDATE_ID_REQUIRED" in result.blockers
    assert "STRATEGY_ID_REQUIRED" in result.blockers
    assert "SYMBOL_REQUIRED" in result.blockers


def test_missing_reason_fields_fail_validation():
    payload = _candidate().to_dict()
    payload["entry_trigger"] = ""
    payload["invalid_if"] = ""
    payload["rank_reason"] = ""

    result = validate_strategy_candidate(payload)

    assert result.valid is False
    assert "ENTRY_TRIGGER_REQUIRED" in result.blockers
    assert "INVALID_IF_REQUIRED" in result.blockers
    assert "RANK_REASON_REQUIRED" in result.blockers


def test_blockers_and_warnings_must_be_string_lists():
    payload = _candidate().to_dict()
    payload["blockers"] = ["", 123]
    payload["warnings"] = "not-a-list"

    result = validate_strategy_candidate(payload)

    assert result.valid is False
    assert "BLOCKERS_MUST_BE_STRING_LIST" in result.blockers
    assert "WARNINGS_MUST_BE_STRING_LIST" in result.blockers


def test_evidence_must_be_dict():
    payload = _candidate().to_dict()
    payload["evidence"] = ["bad"]

    result = validate_strategy_candidate(payload)

    assert result.valid is False
    assert "EVIDENCE_MUST_BE_DICT" in result.blockers


def test_candidate_order_flag_must_remain_false():
    payload = _candidate().to_dict()
    payload["is_order_action"] = True

    result = validate_strategy_candidate(payload)

    assert result.valid is False
    assert "CANDIDATE_ORDER_FLAG_UNSAFE" in result.blockers


def test_no_trade_status_requires_no_trade_direction():
    candidate = _candidate(status=CandidateStatus.NO_TRADE, direction=Direction.BUY_CALL, blockers=("NO_TRADE_CHOP",))

    result = validate_strategy_candidate(candidate)

    assert result.valid is False
    assert "NO_TRADE_STATUS_REQUIRES_NO_TRADE_DIRECTION" in result.blockers


def test_blocked_candidate_without_blocker_gets_warning_not_failure():
    candidate = _candidate(status=CandidateStatus.BLOCKED_CANDIDATE)

    result = validate_strategy_candidate(candidate)

    assert result.valid is True
    assert "BLOCKED_OR_NO_TRADE_WITHOUT_EXPLANATORY_BLOCKER" in result.warnings


def test_valid_no_trade_candidate():
    candidate = _candidate(
        candidate_id="no-trade-1",
        strategy_id="NO_TRADE_CHOP",
        movement_type="CHOP",
        direction=Direction.NO_TRADE,
        status=CandidateStatus.NO_TRADE,
        raw_score=0.9,
        blockers=("NO_TRADE_CHOP",),
        rank_reason="repeated VWAP crosses with no premium expansion",
    )

    result = validate_strategy_candidate(candidate)

    assert result.valid is True
    assert result.warnings == []
    assert candidate.to_dict()["direction"] == "NO_TRADE"


def test_strategy_context_serializes_missing_fields_safely():
    context = StrategyContext(symbol="NIFTY", ts_epoch=123.0)
    payload = context.to_dict()

    assert payload["symbol"] == "NIFTY"
    assert payload["ts_epoch"] == 123.0
    assert payload["spot_ltp"] is None
    assert payload["option_ltp_age_sec"] is None
    assert payload["is_order_action"] is False


def test_validation_result_serializes():
    result = validate_strategy_candidate(None)

    assert result.valid is False
    assert result.to_dict()["blockers"] == ["CANDIDATE_REQUIRED"]
    assert result.to_dict()["is_order_action"] is False

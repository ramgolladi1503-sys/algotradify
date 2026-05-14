from __future__ import annotations

from broker_contract import (
    BrokerContractReadinessStatus,
    build_broker_contract_readiness,
    build_broker_contract_readiness_batch,
)


def _candidate(**overrides):
    payload = {
        "candidate_id": "c1",
        "symbol": "NIFTY",
        "strategy_id": "orb_retest",
        "setup_family": "ORB_RETEST",
        "confidence": 85,
        "entry_hypothesis": {
            "expiry": "2026-05-28",
            "strike": 25500,
            "option_type": "CE",
            "exchange": "NFO",
        },
    }
    payload.update(overrides)
    return payload


def _instrument(strike: float, token: int | str | None = 1000, **overrides):
    row = {
        "symbol": "NIFTY",
        "expiry": "2026-05-28",
        "strike": strike,
        "instrument_type": "CE",
        "exchange": "NFO",
        "tradingsymbol": f"NIFTY26MAY{int(strike)}CE",
        "instrument_token": token,
    }
    row.update(overrides)
    return row


def test_broker_contract_readiness_exact_match():
    result = build_broker_contract_readiness(_candidate(), [_instrument(25500, token=12345)])

    assert result.readiness_status == BrokerContractReadinessStatus.RESOLVED_EXACT
    assert result.resolved is True
    assert result.instrument_token == 12345
    assert result.fallback_used is False
    assert result.blockers == []
    assert result.to_dict()["is_execution_decision"] is False
    assert result.resolution["status"] == "EXACT"


def test_broker_contract_readiness_fallback_is_visible():
    result = build_broker_contract_readiness(
        _candidate(),
        [_instrument(25450, token=11111)],
        max_fallback_distance=60,
    )

    assert result.readiness_status == BrokerContractReadinessStatus.RESOLVED_FALLBACK
    assert result.resolved is True
    assert result.instrument_token == 11111
    assert result.fallback_used is True
    assert result.fallback_distance == 50
    assert "FALLBACK_CONTRACT_USED" in result.warnings
    assert result.resolution["status"] == "FALLBACK"


def test_broker_contract_readiness_not_found_blocks_candidate():
    result = build_broker_contract_readiness(
        _candidate(),
        [_instrument(25000, token=11111), _instrument(26000, token=22222)],
        max_fallback_distance=100,
    )

    assert result.readiness_status == BrokerContractReadinessStatus.BLOCKED_NOT_FOUND
    assert result.resolved is False
    assert result.instrument_token is None
    assert result.fallback_used is False
    assert "OPTION_TOKEN_NOT_FOUND" in result.blockers
    assert result.resolution["status"] == "NOT_FOUND"


def test_broker_contract_readiness_missing_request_fields():
    result = build_broker_contract_readiness(
        _candidate(entry_hypothesis={"expiry": "2026-05-28"}),
        [_instrument(25500, token=12345)],
    )

    assert result.readiness_status == BrokerContractReadinessStatus.BLOCKED_MISSING_REQUEST
    assert result.resolved is False
    assert "MISSING_CONTRACT_STRIKE" in result.blockers
    assert "MISSING_CONTRACT_OPTION_TYPE" in result.blockers
    assert result.resolution is None


def test_broker_contract_readiness_coverage_failure_is_structured():
    result = build_broker_contract_readiness(
        _candidate(),
        [_instrument(25500, token="")],
        min_token_coverage=1,
    )

    assert result.readiness_status == BrokerContractReadinessStatus.BLOCKED_COVERAGE_FAILED
    assert result.resolved is False
    assert result.instrument_token is None
    assert result.blockers == ["TOKEN_COVERAGE_BELOW_THRESHOLD"]
    assert "error" in result.resolution


def test_broker_contract_readiness_preserves_candidate_truth_blockers():
    result = build_broker_contract_readiness(
        _candidate(blockers=["LOW_CONFIDENCE"]),
        [_instrument(25500, token=12345)],
    )

    assert result.readiness_status == BrokerContractReadinessStatus.RESOLVED_EXACT
    assert result.resolved is True
    assert "LOW_CONFIDENCE" in result.blockers


def test_broker_contract_readiness_batch_builds_all_records():
    results = build_broker_contract_readiness_batch(
        [
            _candidate(candidate_id="c1"),
            _candidate(candidate_id="c2", entry_hypothesis={"expiry": "2026-05-28"}),
        ],
        [_instrument(25500, token=12345)],
    )

    assert len(results) == 2
    assert results[0].readiness_status == BrokerContractReadinessStatus.RESOLVED_EXACT
    assert results[1].readiness_status == BrokerContractReadinessStatus.BLOCKED_MISSING_REQUEST

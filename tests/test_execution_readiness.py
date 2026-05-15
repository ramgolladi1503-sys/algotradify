from __future__ import annotations

from execution_readiness import ExecutionReadinessStatus, RiskReadiness, build_execution_readiness


def _candidate_truth(**overrides):
    payload = {
        "candidate_id": "c1",
        "truth_status": "REAL",
        "blockers": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def _opportunity(**overrides):
    payload = {
        "candidate_id": "c1",
        "opportunity_status": "SELECTED",
        "blockers": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def _broker(**overrides):
    payload = {
        "candidate_id": "c1",
        "readiness_status": "RESOLVED_EXACT",
        "resolved": True,
        "fallback_used": False,
        "blockers": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def _market(**overrides):
    payload = {
        "symbol": "NIFTY26MAY25500CE",
        "status": "READY",
        "blockers": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def test_execution_readiness_allows_only_when_all_evidence_passes():
    result = build_execution_readiness(
        candidate_truth=_candidate_truth(),
        opportunity=_opportunity(),
        broker_contract=_broker(),
        market_readiness=_market(),
        risk=RiskReadiness(allowed=True, status="RISK_OK"),
    )

    assert result.execution_allowed is True
    assert result.status == ExecutionReadinessStatus.ALLOWED
    assert result.blockers == []
    assert result.is_order is False
    assert result.to_dict()["is_execution_readiness_record"] is True


def test_execution_readiness_blocks_without_risk_even_if_all_other_evidence_passes():
    result = build_execution_readiness(
        candidate_truth=_candidate_truth(),
        opportunity=_opportunity(),
        broker_contract=_broker(),
        market_readiness=_market(),
        risk=None,
    )

    assert result.execution_allowed is False
    assert result.status == ExecutionReadinessStatus.BLOCKED_INCOMPLETE_EVIDENCE
    assert "MISSING_RISK_READINESS" in result.blockers


def test_execution_readiness_blocks_non_real_candidate_truth():
    result = build_execution_readiness(
        candidate_truth=_candidate_truth(truth_status="FALLBACK"),
        opportunity=_opportunity(),
        broker_contract=_broker(),
        market_readiness=_market(),
        risk=RiskReadiness(allowed=True, status="RISK_OK"),
    )

    assert result.execution_allowed is False
    assert result.status == ExecutionReadinessStatus.BLOCKED_CANDIDATE_TRUTH
    assert "CANDIDATE_TRUTH_NOT_REAL:FALLBACK" in result.blockers


def test_execution_readiness_blocks_unselected_or_blocked_opportunity():
    result = build_execution_readiness(
        candidate_truth=_candidate_truth(),
        opportunity=_opportunity(opportunity_status="BLOCKED"),
        broker_contract=_broker(),
        market_readiness=_market(),
        risk=RiskReadiness(allowed=True, status="RISK_OK"),
    )

    assert result.execution_allowed is False
    assert result.status == ExecutionReadinessStatus.BLOCKED_OPPORTUNITY
    assert "OPPORTUNITY_NOT_RANKABLE:BLOCKED" in result.blockers


def test_execution_readiness_blocks_unresolved_broker_contract():
    result = build_execution_readiness(
        candidate_truth=_candidate_truth(),
        opportunity=_opportunity(),
        broker_contract=_broker(readiness_status="BLOCKED_NOT_FOUND", resolved=False, blockers=["OPTION_TOKEN_NOT_FOUND"]),
        market_readiness=_market(),
        risk=RiskReadiness(allowed=True, status="RISK_OK"),
    )

    assert result.execution_allowed is False
    assert result.status == ExecutionReadinessStatus.BLOCKED_BROKER_CONTRACT
    assert "BROKER_CONTRACT_NOT_RESOLVED:BLOCKED_NOT_FOUND" in result.blockers


def test_execution_readiness_blocks_bad_market_readiness():
    result = build_execution_readiness(
        candidate_truth=_candidate_truth(),
        opportunity=_opportunity(),
        broker_contract=_broker(),
        market_readiness=_market(status="BLOCKED_STALE_QUOTE", blockers=["STALE_OPTION_LTP"]),
        risk=RiskReadiness(allowed=True, status="RISK_OK"),
    )

    assert result.execution_allowed is False
    assert result.status == ExecutionReadinessStatus.BLOCKED_MARKET_READINESS
    assert "MARKET_NOT_READY:BLOCKED_STALE_QUOTE" in result.blockers


def test_execution_readiness_blocks_risk_rejection():
    result = build_execution_readiness(
        candidate_truth=_candidate_truth(),
        opportunity=_opportunity(),
        broker_contract=_broker(),
        market_readiness=_market(),
        risk=RiskReadiness(allowed=False, status="DAILY_LOSS_LIMIT", blockers=["DAILY_LOSS_LIMIT_HIT"]),
    )

    assert result.execution_allowed is False
    assert result.status == ExecutionReadinessStatus.BLOCKED_RISK
    assert "RISK_NOT_ALLOWED:DAILY_LOSS_LIMIT" in result.blockers
    assert "RISK:DAILY_LOSS_LIMIT_HIT" in result.blockers


def test_execution_readiness_fallback_broker_contract_adds_warning_not_blocker():
    result = build_execution_readiness(
        candidate_truth=_candidate_truth(),
        opportunity=_opportunity(),
        broker_contract=_broker(readiness_status="RESOLVED_FALLBACK", fallback_used=True, warnings=["FALLBACK_CONTRACT_USED"]),
        market_readiness=_market(),
        risk=RiskReadiness(allowed=True, status="RISK_OK"),
    )

    assert result.execution_allowed is True
    assert result.status == ExecutionReadinessStatus.ALLOWED
    assert "BROKER_CONTRACT:FALLBACK_CONTRACT_USED" in result.warnings
    assert "BROKER_CONTRACT:FALLBACK_USED" in result.warnings

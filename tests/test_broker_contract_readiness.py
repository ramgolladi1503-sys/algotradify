from __future__ import annotations

from broker_contract import (
    BrokerContractReadinessStatus,
    InstrumentResolutionHealthStatus,
    build_broker_contract_readiness,
    build_broker_contract_readiness_batch,
    build_instrument_resolution_health_panel,
    instrument_resolution_health_schema_contract,
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


def test_instrument_resolution_health_schema_contract_is_safe_and_complete():
    contract = instrument_resolution_health_schema_contract()

    assert contract["schema_version"] == "1.0"
    assert contract["panel_type"] == "INSTRUMENT_RESOLUTION_HEALTH_PANEL"
    assert contract["safe_flags"] == {"read_only": True, "is_order_action": False}
    assert "summary" in contract["required_keys"]
    assert "rows" in contract["required_keys"]
    assert "exact_count" in contract["summary_required_keys"]
    assert "instrument_token" in contract["row_required_keys"]
    assert "resolution_source" in contract["row_required_keys"]


def test_instrument_resolution_health_panel_is_healthy_for_exact_matches():
    record = build_broker_contract_readiness(_candidate(), [_instrument(25500, token=12345)])
    panel = build_instrument_resolution_health_panel([record])
    payload = panel.to_dict()

    assert panel.status == InstrumentResolutionHealthStatus.HEALTHY
    assert payload["panel_type"] == "INSTRUMENT_RESOLUTION_HEALTH_PANEL"
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["summary"]["record_count"] == 1
    assert payload["summary"]["resolved_count"] == 1
    assert payload["summary"]["exact_count"] == 1
    assert payload["summary"]["fallback_count"] == 0
    assert payload["summary"]["missing_token_count"] == 0
    assert payload["summary"]["blocked_count"] == 0
    assert payload["rows"][0]["instrument_token"] == 12345
    assert payload["rows"][0]["resolution_source"] == "EXACT"
    assert payload["rows"][0]["read_only"] is True
    assert payload["rows"][0]["is_order_action"] is False


def test_instrument_resolution_health_panel_degrades_for_fallback_match():
    record = build_broker_contract_readiness(
        _candidate(),
        [_instrument(25450, token=11111)],
        max_fallback_distance=60,
    )
    panel = build_instrument_resolution_health_panel([record])
    payload = panel.to_dict()

    assert panel.status == InstrumentResolutionHealthStatus.DEGRADED_FALLBACK
    assert payload["summary"]["resolved_count"] == 1
    assert payload["summary"]["fallback_count"] == 1
    assert payload["summary"]["unresolved_count"] == 0
    assert payload["rows"][0]["fallback_used"] is True
    assert payload["rows"][0]["fallback_distance"] == 50
    assert payload["rows"][0]["resolution_source"] == "FALLBACK"
    assert "FALLBACK_INSTRUMENT_RESOLUTION_PRESENT" in payload["warnings"]


def test_instrument_resolution_health_panel_blocks_missing_token():
    record = build_broker_contract_readiness(
        _candidate(),
        [_instrument(25500, token="")],
        min_token_coverage=1,
    )
    panel = build_instrument_resolution_health_panel([record])
    payload = panel.to_dict()

    assert panel.status == InstrumentResolutionHealthStatus.BLOCKED_UNRESOLVED
    assert payload["summary"]["resolved_count"] == 0
    assert payload["summary"]["missing_token_count"] == 1
    assert payload["summary"]["blocked_count"] == 1
    assert "MISSING_INSTRUMENT_TOKENS_PRESENT" in payload["blockers"]
    assert payload["rows"][0]["instrument_token"] is None


def test_instrument_resolution_health_panel_blocks_missing_request():
    record = build_broker_contract_readiness(
        _candidate(entry_hypothesis={"expiry": "2026-05-28"}),
        [_instrument(25500, token=12345)],
    )
    panel = build_instrument_resolution_health_panel([record])
    payload = panel.to_dict()

    assert panel.status == InstrumentResolutionHealthStatus.BLOCKED_UNRESOLVED
    assert payload["summary"]["unresolved_count"] == 1
    assert payload["rows"][0]["resolution_source"] == "MISSING_REQUEST"
    assert "UNRESOLVED_INSTRUMENTS_PRESENT" in payload["blockers"]


def test_instrument_resolution_health_panel_blocks_expired_or_mismatched_instrument():
    row = {
        "candidate_id": "c1",
        "symbol": "NIFTY",
        "strategy_id": "orb_retest",
        "readiness_status": "RESOLVED_EXACT",
        "resolved": True,
        "instrument_token": 12345,
        "fallback_used": False,
        "fallback_distance": None,
        "request": {"symbol": "NIFTY", "expiry": "2026-05-28", "strike": 25500, "option_type": "CE", "exchange": "NFO"},
        "resolution": {
            "status": "EXACT",
            "instrument_token": 12345,
            "instrument": {
                "symbol": "NIFTY",
                "expiry": "2026-06-04",
                "strike": 25500,
                "instrument_type": "CE",
                "exchange": "NFO",
                "tradingsymbol": "NIFTY26JUN25500CE",
                "instrument_token": 12345,
            },
        },
        "blockers": [],
        "warnings": [],
    }
    panel = build_instrument_resolution_health_panel([row])
    payload = panel.to_dict()

    assert panel.status == InstrumentResolutionHealthStatus.BLOCKED_UNRESOLVED
    assert payload["summary"]["expired_or_mismatched_count"] == 1
    assert "EXPIRED_OR_MISMATCHED_INSTRUMENTS_PRESENT" in payload["blockers"]
    assert "INSTRUMENT_MISMATCH_EXPIRY" in payload["rows"][0]["blockers"]
    assert payload["rows"][0]["expiry"] == "2026-06-04"


def test_instrument_resolution_health_panel_empty_state_is_safe():
    panel = build_instrument_resolution_health_panel([])
    payload = panel.to_dict()

    assert panel.status == InstrumentResolutionHealthStatus.EMPTY
    assert payload["summary"]["record_count"] == 0
    assert payload["summary"]["resolved_count"] == 0
    assert payload["summary"]["blocked_count"] == 0
    assert payload["rows"] == []
    assert "NO_INSTRUMENT_RESOLUTION_RECORDS" in payload["blockers"]
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False

from __future__ import annotations

import pytest

from broker_contract import (
    BrokerContractResolutionStatus,
    OptionContractRequest,
    TokenCoverageError,
    resolve_option_contract,
)


def _instrument(strike: float, token: int | None = 1000, **overrides):
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


def _request(strike: float = 25500) -> OptionContractRequest:
    return OptionContractRequest(symbol="nifty", expiry="2026-05-28", strike=strike, option_type="ce")


def test_resolve_option_contract_exact_match():
    instruments = [_instrument(25500, token=12345), _instrument(25600, token=22222)]

    result = resolve_option_contract(_request(25500), instruments)

    assert result.status == BrokerContractResolutionStatus.EXACT
    assert result.resolved is True
    assert result.instrument_token == 12345
    assert result.fallback_used is False
    assert result.reason == "EXACT_CONTRACT_MATCH"
    assert result.blockers == []
    assert result.to_dict()["is_execution_decision"] is False


def test_resolve_option_contract_safe_fallback_match():
    instruments = [_instrument(25450, token=11111), _instrument(25650, token=22222)]

    result = resolve_option_contract(_request(25500), instruments, max_fallback_distance=60)

    assert result.status == BrokerContractResolutionStatus.FALLBACK
    assert result.resolved is True
    assert result.instrument_token == 11111
    assert result.fallback_used is True
    assert result.fallback_distance == 50
    assert result.reason == "SAFE_FALLBACK_CONTRACT_MATCH"
    assert result.warnings == ["FALLBACK_CONTRACT_USED"]


def test_resolve_option_contract_no_exact_no_fallback_returns_not_found_without_crashing():
    instruments = [_instrument(25000, token=11111), _instrument(26000, token=22222)]

    result = resolve_option_contract(_request(25500), instruments, max_fallback_distance=100)

    assert result.status == BrokerContractResolutionStatus.NOT_FOUND
    assert result.resolved is False
    assert result.instrument is None
    assert result.instrument_token is None
    assert result.fallback_used is False
    assert result.reason == "OPTION_TOKEN_NOT_FOUND"
    assert result.blockers == ["OPTION_TOKEN_NOT_FOUND"]


def test_resolve_option_contract_no_fallback_allowed_returns_not_found():
    instruments = [_instrument(25450, token=11111)]

    result = resolve_option_contract(_request(25500), instruments, allow_fallback=False)

    assert result.status == BrokerContractResolutionStatus.NOT_FOUND
    assert result.resolved is False
    assert result.instrument is None
    assert result.blockers == ["OPTION_TOKEN_NOT_FOUND"]


def test_resolve_option_contract_invalid_request_returns_structured_blocker():
    result = resolve_option_contract(
        OptionContractRequest(symbol="", expiry="2026-05-28", strike=-1, option_type="XX"),
        [_instrument(25500, token=12345)],
    )

    assert result.status == BrokerContractResolutionStatus.INVALID_REQUEST
    assert result.resolved is False
    assert result.reason == "INVALID_OPTION_CONTRACT_REQUEST"
    assert result.blockers == ["INVALID_OPTION_CONTRACT_REQUEST"]


def test_resolve_option_contract_token_coverage_below_threshold_raises():
    instruments = [_instrument(25500, token="")]

    with pytest.raises(TokenCoverageError):
        resolve_option_contract(_request(25500), instruments, min_token_coverage=1)


def test_resolve_option_contract_ignores_wrong_family_contracts():
    instruments = [
        _instrument(25500, token=12345, symbol="BANKNIFTY"),
        _instrument(25500, token=22222, instrument_type="PE"),
        _instrument(25500, token=33333, expiry="2026-06-04"),
        _instrument(25600, token=44444),
    ]

    result = resolve_option_contract(_request(25500), instruments, max_fallback_distance=150)

    assert result.status == BrokerContractResolutionStatus.FALLBACK
    assert result.instrument_token == 44444
    assert result.fallback_distance == 100

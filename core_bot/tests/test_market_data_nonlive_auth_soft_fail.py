from __future__ import annotations

import pytest

from config import config as cfg
from core import market_data


class _AuthFailKiteClient:
    def __init__(self) -> None:
        self.kite = object()

    def ensure(self):
        return self.kite

    def resolve_index_token(self, _symbol: str):
        return 256265

    def historical_data(self, *args, **kwargs):
        raise RuntimeError("TokenException('Incorrect `api_key` or `access_token`.')")

    def _is_historical_auth_error(self, _exc: Exception) -> bool:
        return True


def _reset_warmup_state():
    market_data._WARMUP_SEED_ATTEMPTS.clear()
    market_data._WARMUP_SEED_DETAILS.clear()


def test_nonlive_warm_seed_auth_failure_soft_degrades(monkeypatch):
    _reset_warmup_state()
    monkeypatch.setattr(market_data, "kite_client", _AuthFailKiteClient())
    monkeypatch.setattr(cfg, "NONLIVE_WARMUP_AUTH_SOFT_FAIL", True, raising=False)
    monkeypatch.setattr(cfg, "STARTUP_WARMUP_FETCH_RETRIES", 1, raising=False)
    monkeypatch.setattr(cfg, "NONLIVE_STARTUP_WARMUP_MAX_HIST_EMPTY_ATTEMPTS", 1, raising=False)

    bars, seeded_ok, reason = market_data._warm_seed_ohlc_from_history(
        symbol="NIFTY",
        bars=[],
        min_bars=30,
        interval="minute",
        windows_minutes=[60],
        required_seed_bars=30,
        startup_phase=True,
        market_mode="SIM",
    )

    assert bars == []
    assert seeded_ok is False
    assert reason == "HIST_FETCH_FAILED"
    assert market_data._WARMUP_SEED_DETAILS["NIFTY"]["warmup_degraded_detail"] == "auth_failed_nonlive"


def test_live_warm_seed_auth_failure_still_raises(monkeypatch):
    _reset_warmup_state()
    monkeypatch.setattr(market_data, "kite_client", _AuthFailKiteClient())
    monkeypatch.setattr(cfg, "NONLIVE_WARMUP_AUTH_SOFT_FAIL", True, raising=False)
    monkeypatch.setattr(cfg, "STARTUP_WARMUP_FETCH_RETRIES", 1, raising=False)

    with pytest.raises(RuntimeError):
        market_data._warm_seed_ohlc_from_history(
            symbol="NIFTY",
            bars=[],
            min_bars=30,
            interval="minute",
            windows_minutes=[60],
            required_seed_bars=30,
            startup_phase=True,
            market_mode="LIVE",
        )

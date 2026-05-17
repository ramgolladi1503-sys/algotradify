from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StrategyContext:
    """Shared read-only context for movement strategies.

    All fields except symbol and timestamp are optional because missing market
    evidence must become blockers/warnings, not runtime crashes.
    """

    symbol: str
    ts_epoch: float
    spot_ltp: float | None = None
    vwap: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    orb_high: float | None = None
    orb_low: float | None = None
    prev_day_high: float | None = None
    prev_day_low: float | None = None
    atr: float | None = None
    atr_short: float | None = None
    atr_long: float | None = None
    range_width_pct: float | None = None
    volume_z: float | None = None
    volatility_state: str | None = None
    regime_hint: str | None = None
    option_ce_ltp: float | None = None
    option_pe_ltp: float | None = None
    ce_premium_change: float | None = None
    pe_premium_change: float | None = None
    ce_spread_pct: float | None = None
    pe_spread_pct: float | None = None
    ce_depth: float | None = None
    pe_depth: float | None = None
    option_ltp_age_sec: float | None = None
    quote_source: str | None = None
    time_of_day: str | None = None
    minutes_since_open: int | None = None
    minutes_to_close: int | None = None
    expiry_context: str | None = None

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "ts_epoch": self.ts_epoch,
            "spot_ltp": self.spot_ltp,
            "vwap": self.vwap,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "orb_high": self.orb_high,
            "orb_low": self.orb_low,
            "prev_day_high": self.prev_day_high,
            "prev_day_low": self.prev_day_low,
            "atr": self.atr,
            "atr_short": self.atr_short,
            "atr_long": self.atr_long,
            "range_width_pct": self.range_width_pct,
            "volume_z": self.volume_z,
            "volatility_state": self.volatility_state,
            "regime_hint": self.regime_hint,
            "option_ce_ltp": self.option_ce_ltp,
            "option_pe_ltp": self.option_pe_ltp,
            "ce_premium_change": self.ce_premium_change,
            "pe_premium_change": self.pe_premium_change,
            "ce_spread_pct": self.ce_spread_pct,
            "pe_spread_pct": self.pe_spread_pct,
            "ce_depth": self.ce_depth,
            "pe_depth": self.pe_depth,
            "option_ltp_age_sec": self.option_ltp_age_sec,
            "quote_source": self.quote_source,
            "time_of_day": self.time_of_day,
            "minutes_since_open": self.minutes_since_open,
            "minutes_to_close": self.minutes_to_close,
            "expiry_context": self.expiry_context,
            "is_order_action": self.is_order_action,
        }

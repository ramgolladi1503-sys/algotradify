from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MarketReadinessStatus(StrEnum):
    READY = "READY"
    BLOCKED_STALE_QUOTE = "BLOCKED_STALE_QUOTE"
    BLOCKED_STALE_DEPTH = "BLOCKED_STALE_DEPTH"
    BLOCKED_SPREAD_TOO_WIDE = "BLOCKED_SPREAD_TOO_WIDE"
    BLOCKED_SLIPPAGE_BUDGET = "BLOCKED_SLIPPAGE_BUDGET"
    BLOCKED_MISSING_QUOTE = "BLOCKED_MISSING_QUOTE"


@dataclass(frozen=True)
class QuoteSnapshot:
    symbol: str
    ltp: float | None = None
    bid: float | None = None
    ask: float | None = None
    quote_age_sec: float | None = None
    depth_age_sec: float | None = None
    source: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def spread(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return max(0.0, float(self.ask) - float(self.bid))

    @property
    def mid(self) -> float | None:
        if self.bid is None or self.ask is None:
            return self.ltp
        return (float(self.bid) + float(self.ask)) / 2

    @property
    def spread_pct(self) -> float | None:
        spread = self.spread
        mid = self.mid
        if spread is None or mid in (None, 0):
            return None
        return (spread / float(mid)) * 100


@dataclass(frozen=True)
class MarketReadiness:
    symbol: str
    status: MarketReadinessStatus
    quote: dict[str, Any]
    fresh_quote: bool
    fresh_depth: bool
    liquidity_ok: bool
    slippage_budget_ok: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_execution_decision(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "status": self.status.value,
            "quote": dict(self.quote),
            "fresh_quote": self.fresh_quote,
            "fresh_depth": self.fresh_depth,
            "liquidity_ok": self.liquidity_ok,
            "slippage_budget_ok": self.slippage_budget_ok,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "is_execution_decision": self.is_execution_decision,
        }


def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def quote_from_mapping(row: dict[str, Any]) -> QuoteSnapshot:
    return QuoteSnapshot(
        symbol=str(row.get("symbol") or row.get("tradingsymbol") or row.get("instrument") or "").upper(),
        ltp=_num(row.get("ltp") or row.get("last_price") or row.get("last_traded_price")),
        bid=_num(row.get("bid") or row.get("best_bid") or row.get("buy_price")),
        ask=_num(row.get("ask") or row.get("best_ask") or row.get("sell_price")),
        quote_age_sec=_num(row.get("quote_age_sec") or row.get("ltp_age_sec") or row.get("age_sec")),
        depth_age_sec=_num(row.get("depth_age_sec") or row.get("market_depth_age_sec")),
        source=row.get("source") or row.get("quote_source"),
        raw=dict(row),
    )


def evaluate_market_readiness(
    quote: QuoteSnapshot | dict[str, Any] | None,
    *,
    max_quote_age_sec: float = 2.0,
    max_depth_age_sec: float = 2.0,
    max_spread_pct: float = 1.0,
    slippage_budget_pct: float = 1.5,
) -> MarketReadiness:
    if quote is None:
        return MarketReadiness(
            symbol="UNKNOWN",
            status=MarketReadinessStatus.BLOCKED_MISSING_QUOTE,
            quote={},
            fresh_quote=False,
            fresh_depth=False,
            liquidity_ok=False,
            slippage_budget_ok=False,
            blockers=["MISSING_QUOTE"],
        )

    snapshot = quote_from_mapping(quote) if isinstance(quote, dict) else quote
    blockers: list[str] = []
    warnings: list[str] = []

    fresh_quote = snapshot.quote_age_sec is not None and snapshot.quote_age_sec <= max_quote_age_sec
    fresh_depth = snapshot.depth_age_sec is not None and snapshot.depth_age_sec <= max_depth_age_sec

    if snapshot.ltp is None:
        blockers.append("MISSING_LTP")
    if not fresh_quote:
        blockers.append("STALE_OPTION_LTP")
    if not fresh_depth:
        blockers.append("STALE_DEPTH")

    spread_pct = snapshot.spread_pct
    liquidity_ok = spread_pct is not None and spread_pct <= max_spread_pct
    slippage_budget_ok = spread_pct is not None and spread_pct <= slippage_budget_pct

    if spread_pct is None:
        blockers.append("MISSING_BID_ASK")
    elif not liquidity_ok:
        blockers.append("SPREAD_TOO_WIDE")

    if not slippage_budget_ok:
        blockers.append("SLIPPAGE_BUDGET_EXCEEDED")

    status = _status_from_blockers(blockers)
    quote_payload = {
        "symbol": snapshot.symbol,
        "ltp": snapshot.ltp,
        "bid": snapshot.bid,
        "ask": snapshot.ask,
        "quote_age_sec": snapshot.quote_age_sec,
        "depth_age_sec": snapshot.depth_age_sec,
        "source": snapshot.source,
        "spread": snapshot.spread,
        "spread_pct": spread_pct,
        "max_quote_age_sec": max_quote_age_sec,
        "max_depth_age_sec": max_depth_age_sec,
        "max_spread_pct": max_spread_pct,
        "slippage_budget_pct": slippage_budget_pct,
        "raw": dict(snapshot.raw),
    }

    if snapshot.source in (None, ""):
        warnings.append("QUOTE_SOURCE_MISSING")

    return MarketReadiness(
        symbol=snapshot.symbol or "UNKNOWN",
        status=status,
        quote=quote_payload,
        fresh_quote=fresh_quote,
        fresh_depth=fresh_depth,
        liquidity_ok=liquidity_ok,
        slippage_budget_ok=slippage_budget_ok,
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
    )


def evaluate_market_readiness_batch(
    quotes: list[QuoteSnapshot | dict[str, Any]],
    **kwargs: Any,
) -> list[MarketReadiness]:
    return [evaluate_market_readiness(quote, **kwargs) for quote in quotes]


def _status_from_blockers(blockers: list[str]) -> MarketReadinessStatus:
    if "MISSING_QUOTE" in blockers or "MISSING_LTP" in blockers or "MISSING_BID_ASK" in blockers:
        return MarketReadinessStatus.BLOCKED_MISSING_QUOTE
    if "STALE_OPTION_LTP" in blockers:
        return MarketReadinessStatus.BLOCKED_STALE_QUOTE
    if "STALE_DEPTH" in blockers:
        return MarketReadinessStatus.BLOCKED_STALE_DEPTH
    if "SPREAD_TOO_WIDE" in blockers:
        return MarketReadinessStatus.BLOCKED_SPREAD_TOO_WIDE
    if "SLIPPAGE_BUDGET_EXCEEDED" in blockers:
        return MarketReadinessStatus.BLOCKED_SLIPPAGE_BUDGET
    return MarketReadinessStatus.READY


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

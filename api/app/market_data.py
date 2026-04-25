from collections import deque
from datetime import datetime, timezone
from typing import Dict, Deque, Optional, List
from pydantic import BaseModel, Field


class MarketTick(BaseModel):
    symbol: str
    ltp: Optional[float] = Field(default=None, gt=0)
    bid: Optional[float] = Field(default=None, gt=0)
    ask: Optional[float] = Field(default=None, gt=0)
    volume: Optional[int] = Field(default=None, ge=0)
    oi: Optional[int] = Field(default=None, ge=0)
    iv: Optional[float] = Field(default=None, ge=0)
    source: str = "manual"
    fallback_used: bool = False
    timestamp: Optional[str] = None


class MarketSnapshot(BaseModel):
    symbol: str
    ltp: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    oi: Optional[int] = None
    iv: Optional[float] = None
    source: str
    updated_at: str
    quote_age_sec: float
    spread_pct: Optional[float] = None
    data_quality: str
    execution_allowed: bool
    blockers: List[str] = []
    warnings: List[str] = []
    liquidity_score: float = Field(ge=0, le=1)


class MarketDataStore:
    def __init__(self, max_ticks: int = 500):
        self.max_ticks = max_ticks
        self.ticks: Dict[str, Deque[MarketTick]] = {}
        self.snapshots: Dict[str, MarketSnapshot] = {}

    def ingest_tick(self, tick: MarketTick) -> MarketSnapshot:
        symbol = tick.symbol.upper().strip()
        clean_tick = tick.model_copy(update={
            "symbol": symbol,
            "timestamp": tick.timestamp or self._now_iso(),
        })
        self.ticks.setdefault(symbol, deque(maxlen=self.max_ticks)).append(clean_tick)
        snapshot = self._build_snapshot(clean_tick)
        self.snapshots[symbol] = snapshot
        return snapshot

    def get_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        snap = self.snapshots.get(symbol.upper().strip())
        if not snap:
            return None
        return self._refresh_age_and_quality(snap)

    def all_snapshots(self) -> List[MarketSnapshot]:
        return [self._refresh_age_and_quality(s) for s in self.snapshots.values()]

    def quality_summary(self) -> dict:
        counts = {"tradable": 0, "partial": 0, "stale": 0, "fallback": 0, "invalid": 0}
        for snap in self.all_snapshots():
            counts[snap.data_quality] = counts.get(snap.data_quality, 0) + 1
        return {"counts": counts, "total": sum(counts.values())}

    def stale_snapshots(self) -> List[MarketSnapshot]:
        return [s for s in self.all_snapshots() if s.data_quality in {"stale", "fallback", "invalid"}]

    def _build_snapshot(self, tick: MarketTick) -> MarketSnapshot:
        now = datetime.now(timezone.utc)
        tick_time = self._parse_time(tick.timestamp) if tick.timestamp else now
        age = max((now - tick_time).total_seconds(), 0.0)
        spread_pct = self._spread_pct(tick.bid, tick.ask)
        quality, allowed, blockers, warnings = self._classify(tick, age, spread_pct)
        liquidity_score = self._liquidity_score(spread_pct, quality)

        return MarketSnapshot(
            symbol=tick.symbol,
            ltp=tick.ltp,
            bid=tick.bid,
            ask=tick.ask,
            volume=tick.volume,
            oi=tick.oi,
            iv=tick.iv,
            source=tick.source,
            updated_at=tick.timestamp or self._now_iso(),
            quote_age_sec=round(age, 3),
            spread_pct=spread_pct,
            data_quality=quality,
            execution_allowed=allowed,
            blockers=blockers,
            warnings=warnings,
            liquidity_score=liquidity_score,
        )

    def _refresh_age_and_quality(self, snap: MarketSnapshot) -> MarketSnapshot:
        tick = MarketTick(
            symbol=snap.symbol,
            ltp=snap.ltp,
            bid=snap.bid,
            ask=snap.ask,
            volume=snap.volume,
            oi=snap.oi,
            iv=snap.iv,
            source=snap.source,
            fallback_used=snap.data_quality == "fallback",
            timestamp=snap.updated_at,
        )
        return self._build_snapshot(tick)

    def _classify(self, tick: MarketTick, age: float, spread_pct: Optional[float]):
        blockers = []
        warnings = []

        if tick.fallback_used or tick.source.lower() in {"fallback", "synthetic", "estimated"}:
            return "fallback", False, ["FALLBACK_DATA"], ["Fallback data is advisory only"]

        if tick.ltp is None:
            return "invalid", False, ["LTP_MISSING"], ["No live LTP"]

        if age > 5:
            return "stale", False, ["STALE_QUOTE"], [f"Quote age {round(age, 2)}s exceeds threshold"]

        if tick.bid is None or tick.ask is None:
            return "partial", False, ["DEPTH_MISSING"], ["Bid/ask depth missing"]

        if tick.ask < tick.bid:
            return "invalid", False, ["CROSSED_MARKET"], ["Ask is below bid"]

        if spread_pct is not None and spread_pct > 3.0:
            return "partial", False, ["HIGH_SPREAD"], [f"Spread {round(spread_pct, 2)}% is too wide"]

        return "tradable", True, blockers, warnings

    def _spread_pct(self, bid: Optional[float], ask: Optional[float]) -> Optional[float]:
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            return None
        mid = (bid + ask) / 2
        if mid <= 0:
            return None
        return round(((ask - bid) / mid) * 100, 4)

    def _liquidity_score(self, spread_pct: Optional[float], quality: str) -> float:
        if quality in {"fallback", "invalid", "stale"}:
            return 0.0
        if spread_pct is None:
            return 0.25
        return round(max(0.0, min(1.0, 1 - (spread_pct / 3.0))), 4)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _parse_time(self, value: str) -> datetime:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)

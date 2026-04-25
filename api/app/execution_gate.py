from collections import defaultdict, deque
from pydantic import BaseModel, Field


class GateDecision(BaseModel):
    status: str
    execution_allowed: bool
    primary_blocker: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GateThresholds(BaseModel):
    min_score: float = 0.62
    min_confidence: float = 0.58
    min_liquidity: float = 0.45
    max_spread_pct: float = 3.0
    max_quote_age_sec: float = 5.0


class ExecutionGate:
    def __init__(self):
        self.thresholds = {
            "trending": GateThresholds(min_score=0.62, min_confidence=0.58, min_liquidity=0.45, max_spread_pct=3.0),
            "sideways": GateThresholds(min_score=0.66, min_confidence=0.60, min_liquidity=0.55, max_spread_pct=2.0),
            "volatile": GateThresholds(min_score=0.70, min_confidence=0.64, min_liquidity=0.60, max_spread_pct=2.5),
        }
        self.reward_history = defaultdict(lambda: deque(maxlen=30))
        self.adjustment_log = []

    def evaluate(self, candidate, snapshot) -> GateDecision:
        t = self._profile(candidate.regime)
        blockers = []
        warnings = []

        if snapshot.data_quality in {"fallback", "invalid", "stale"}:
            blockers.append(f"DATA_{snapshot.data_quality.upper()}")

        if not snapshot.execution_allowed:
            blockers.extend(snapshot.blockers or ["SNAPSHOT_NOT_EXECUTABLE"])

        if snapshot.quote_age_sec > t.max_quote_age_sec:
            blockers.append("QUOTE_TOO_OLD")

        if snapshot.spread_pct is None:
            blockers.append("SPREAD_UNKNOWN")
        elif snapshot.spread_pct > t.max_spread_pct:
            blockers.append("SPREAD_TOO_WIDE")

        if candidate.liquidity < t.min_liquidity:
            blockers.append("LIQUIDITY_TOO_LOW")

        if candidate.confidence < t.min_confidence:
            blockers.append("CONFIDENCE_TOO_LOW")

        if candidate.score < t.min_score:
            blockers.append("SCORE_TOO_LOW")

        if snapshot.data_quality == "partial":
            warnings.append("PARTIAL_MARKET_DATA")

        unique_blockers = list(dict.fromkeys(blockers))
        unique_warnings = list(dict.fromkeys(warnings + (snapshot.warnings or [])))

        if unique_blockers:
            return GateDecision(
                status="BLOCKED",
                execution_allowed=False,
                primary_blocker=unique_blockers[0],
                blockers=unique_blockers,
                warnings=unique_warnings,
            )

        if unique_warnings:
            return GateDecision(
                status="WATCH",
                execution_allowed=False,
                primary_blocker=unique_warnings[0],
                blockers=[],
                warnings=unique_warnings,
            )

        return GateDecision(status="READY", execution_allowed=True, blockers=[], warnings=[])

    def update_from_reward(self, regime: str, reward: float) -> dict:
        key = regime if regime in self.thresholds else "volatile"
        self.reward_history[key].append(reward)
        history = list(self.reward_history[key])
        if len(history) < 5:
            return {"updated": False, "reason": "insufficient_samples", "samples": len(history)}

        avg_reward = sum(history) / len(history)
        old = self.thresholds[key].model_copy()
        step = 0.01

        if avg_reward < -0.25:
            self._tighten(key, step)
            action = "tightened"
        elif avg_reward > 0.45:
            self._loosen(key, step)
            action = "loosened"
        else:
            action = "unchanged"

        new = self.thresholds[key]
        event = {
            "regime": key,
            "action": action,
            "avg_reward": round(avg_reward, 4),
            "samples": len(history),
            "old": old.model_dump(),
            "new": new.model_dump(),
        }
        self.adjustment_log.append(event)
        self.adjustment_log = self.adjustment_log[-100:]
        return event

    def state(self) -> dict:
        return {
            "thresholds": {k: v.model_dump() for k, v in self.thresholds.items()},
            "reward_history": {k: list(v) for k, v in self.reward_history.items()},
            "adjustments": self.adjustment_log[-20:],
        }

    def _profile(self, regime: str) -> GateThresholds:
        return self.thresholds.get(regime, self.thresholds["volatile"])

    def _tighten(self, regime: str, step: float):
        t = self.thresholds[regime]
        t.min_score = min(0.85, t.min_score + step)
        t.min_confidence = min(0.82, t.min_confidence + step)
        t.min_liquidity = min(0.75, t.min_liquidity + step)
        t.max_spread_pct = max(1.0, t.max_spread_pct - step * 10)

    def _loosen(self, regime: str, step: float):
        t = self.thresholds[regime]
        t.min_score = max(0.55, t.min_score - step)
        t.min_confidence = max(0.50, t.min_confidence - step)
        t.min_liquidity = max(0.35, t.min_liquidity - step)
        t.max_spread_pct = min(4.0, t.max_spread_pct + step * 10)

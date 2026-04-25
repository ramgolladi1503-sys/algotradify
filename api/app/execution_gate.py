from pydantic import BaseModel, Field


class GateDecision(BaseModel):
    status: str
    execution_allowed: bool
    primary_blocker: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExecutionGate:
    def __init__(
        self,
        min_score: float = 0.62,
        min_confidence: float = 0.58,
        min_liquidity: float = 0.45,
        max_spread_pct: float = 3.0,
        max_quote_age_sec: float = 5.0,
    ):
        self.min_score = min_score
        self.min_confidence = min_confidence
        self.min_liquidity = min_liquidity
        self.max_spread_pct = max_spread_pct
        self.max_quote_age_sec = max_quote_age_sec

    def evaluate(self, candidate, snapshot) -> GateDecision:
        blockers = []
        warnings = []

        if snapshot.data_quality in {"fallback", "invalid", "stale"}:
            blockers.append(f"DATA_{snapshot.data_quality.upper()}")

        if not snapshot.execution_allowed:
            blockers.extend(snapshot.blockers or ["SNAPSHOT_NOT_EXECUTABLE"])

        if snapshot.quote_age_sec > self.max_quote_age_sec:
            blockers.append("QUOTE_TOO_OLD")

        if snapshot.spread_pct is None:
            blockers.append("SPREAD_UNKNOWN")
        elif snapshot.spread_pct > self.max_spread_pct:
            blockers.append("SPREAD_TOO_WIDE")

        if candidate.liquidity < self.min_liquidity:
            blockers.append("LIQUIDITY_TOO_LOW")

        if candidate.confidence < self.min_confidence:
            blockers.append("CONFIDENCE_TOO_LOW")

        if candidate.score < self.min_score:
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

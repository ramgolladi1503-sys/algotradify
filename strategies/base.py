from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

VALID_DIRECTIONS = {"BULLISH", "BEARISH", "NEUTRAL"}


@dataclass(frozen=True)
class StrategyContext:
    """Input context passed to strategies.

    This is intentionally generic for PR 3. Later PRs can enrich the context
    with typed market snapshots, breadth, depth, regime, and runtime state.
    """

    symbol: str
    market_regime: str | None = None
    timestamp_epoch: float | int | None = None
    features: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyCandidateDraft:
    """Normalized strategy output before truth/readiness/execution layers.

    A draft is not executable. It is a hypothesis emitted by a strategy.
    Broker contract resolution, quote freshness, risk, liquidity, and execution
    readiness must be applied later.
    """

    candidate_id: str
    symbol: str
    strategy_id: str
    setup_family: str
    direction: str
    confidence: float
    entry_hypothesis: dict[str, Any]
    invalidation_hypothesis: dict[str, Any]
    required_market_regime: str | None = None
    required_data: list[str] = field(default_factory=list)
    signal_features: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id is required")
        if not self.symbol:
            raise ValueError("symbol is required")
        if not self.strategy_id:
            raise ValueError("strategy_id is required")
        if self.direction not in VALID_DIRECTIONS:
            raise ValueError(f"direction must be one of {sorted(VALID_DIRECTIONS)}")
        if not 0 <= float(self.confidence) <= 100:
            raise ValueError("confidence must be between 0 and 100")

    @property
    def is_execution_decision(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "strategy_id": self.strategy_id,
            "setup_family": self.setup_family,
            "direction": self.direction,
            "confidence": self.confidence,
            "entry_hypothesis": self.entry_hypothesis,
            "invalidation_hypothesis": self.invalidation_hypothesis,
            "required_market_regime": self.required_market_regime,
            "required_data": list(self.required_data),
            "signal_features": dict(self.signal_features),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "provenance": dict(self.provenance),
            "raw": dict(self.raw),
            "is_execution_decision": self.is_execution_decision,
        }


class BaseStrategy(Protocol):
    strategy_id: str
    setup_family: str
    display_name: str
    required_data: tuple[str, ...]

    def generate(self, context: StrategyContext) -> list[StrategyCandidateDraft]:
        """Return normalized candidate drafts. Never return executable trades."""

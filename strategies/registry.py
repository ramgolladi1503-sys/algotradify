from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from strategies.base import BaseStrategy, StrategyCandidateDraft, StrategyContext
from strategies.simple_signal import (
    BreadthAlignmentStrategy,
    ExpiryMomentumStrategy,
    FailedBreakoutReversalStrategy,
    OrbRetestStrategy,
    RangeReversionStrategy,
    TrendPullbackStrategy,
    VwapReclaimStrategy,
)


@dataclass
class StrategyRegistry:
    """Registry for candidate-producing strategies.

    Registry output is still pre-truth-layer and pre-readiness-layer. It should
    feed PR 4 Candidate Truth Layer, not execution directly.
    """

    _strategies: dict[str, BaseStrategy] = field(default_factory=dict)

    def register(self, strategy: BaseStrategy) -> None:
        if strategy.strategy_id in self._strategies:
            raise ValueError(f"strategy already registered: {strategy.strategy_id}")
        self._strategies[strategy.strategy_id] = strategy

    def get(self, strategy_id: str) -> BaseStrategy:
        try:
            return self._strategies[strategy_id]
        except KeyError as exc:
            raise KeyError(f"unknown strategy: {strategy_id}") from exc

    def list(self) -> list[dict[str, object]]:
        return [
            {
                "strategy_id": strategy.strategy_id,
                "setup_family": strategy.setup_family,
                "display_name": strategy.display_name,
                "required_data": list(strategy.required_data),
            }
            for strategy in self._strategies.values()
        ]

    def generate_all(self, context: StrategyContext, *, strategy_ids: Iterable[str] | None = None) -> list[StrategyCandidateDraft]:
        selected_ids = list(strategy_ids) if strategy_ids is not None else list(self._strategies)
        drafts: list[StrategyCandidateDraft] = []
        for strategy_id in selected_ids:
            strategy = self.get(strategy_id)
            drafts.extend(strategy.generate(context))
        return drafts


def build_default_strategy_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    for strategy in (
        OrbRetestStrategy(),
        VwapReclaimStrategy(),
        TrendPullbackStrategy(),
        FailedBreakoutReversalStrategy(),
        RangeReversionStrategy(),
        ExpiryMomentumStrategy(),
        BreadthAlignmentStrategy(),
    ):
        registry.register(strategy)
    return registry

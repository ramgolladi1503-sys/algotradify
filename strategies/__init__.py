"""Strategy contract and registry layer for Algotradify.

Strategies in this package emit normalized candidate drafts only. They must not
mark trades executable, resolve broker contracts, or bypass readiness gates.
"""

from strategies.base import BaseStrategy, StrategyCandidateDraft, StrategyContext
from strategies.registry import StrategyRegistry, build_default_strategy_registry

__all__ = [
    "BaseStrategy",
    "StrategyCandidateDraft",
    "StrategyContext",
    "StrategyRegistry",
    "build_default_strategy_registry",
]

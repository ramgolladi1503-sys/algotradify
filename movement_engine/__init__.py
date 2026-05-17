"""Movement opportunity engine contracts.

Movement candidates are proposals only. They do not place orders, call broker
APIs, or mutate execution state.
"""

from movement_engine.context import StrategyContext
from movement_engine.contract import (
    CandidateStatus,
    Direction,
    MovementCandidateValidationResult,
    StrategyCandidate,
    candidate_from_mapping,
    validate_strategy_candidate,
)
from movement_engine.regime import (
    MovementRegime,
    MovementRegimeResult,
    classify_movement_regime,
)

__all__ = [
    "CandidateStatus",
    "Direction",
    "MovementCandidateValidationResult",
    "MovementRegime",
    "MovementRegimeResult",
    "StrategyCandidate",
    "StrategyContext",
    "candidate_from_mapping",
    "classify_movement_regime",
    "validate_strategy_candidate",
]

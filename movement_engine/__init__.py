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

__all__ = [
    "CandidateStatus",
    "Direction",
    "MovementCandidateValidationResult",
    "StrategyCandidate",
    "StrategyContext",
    "candidate_from_mapping",
    "validate_strategy_candidate",
]

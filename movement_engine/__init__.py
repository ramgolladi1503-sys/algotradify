"""Movement opportunity engine contracts.

Movement candidates are proposals only. They do not place orders, call broker
APIs, or mutate execution state.
"""

from movement_engine.candidate_pool import (
    HARD_POOL_BLOCKERS,
    CandidatePoolResult,
    CandidatePoolSummary,
    build_candidate_pool,
)
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
from movement_engine.registry import (
    MovementProviderRegistrationResult,
    MovementRegistryRunResult,
    MovementStrategyProvider,
    MovementStrategyRegistry,
)

__all__ = [
    "CandidatePoolResult",
    "CandidatePoolSummary",
    "CandidateStatus",
    "Direction",
    "HARD_POOL_BLOCKERS",
    "MovementCandidateValidationResult",
    "MovementProviderRegistrationResult",
    "MovementRegime",
    "MovementRegimeResult",
    "MovementRegistryRunResult",
    "MovementStrategyProvider",
    "MovementStrategyRegistry",
    "StrategyCandidate",
    "StrategyContext",
    "build_candidate_pool",
    "candidate_from_mapping",
    "classify_movement_regime",
    "validate_strategy_candidate",
]

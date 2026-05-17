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
from movement_engine.providers import (
    OPENING_DRIVE_PROVIDER_ID,
    ORB_RETEST_PROVIDER_ID,
    opening_drive_provider,
    orb_retest_provider,
    register_opening_drive_orb_providers,
)
from movement_engine.providers.opening_drive_orb import build_opening_drive_orb_candidate_pool
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
    "OPENING_DRIVE_PROVIDER_ID",
    "ORB_RETEST_PROVIDER_ID",
    "StrategyCandidate",
    "StrategyContext",
    "build_candidate_pool",
    "build_opening_drive_orb_candidate_pool",
    "candidate_from_mapping",
    "classify_movement_regime",
    "opening_drive_provider",
    "orb_retest_provider",
    "register_opening_drive_orb_providers",
    "validate_strategy_candidate",
]

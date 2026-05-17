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
    COMPRESSION_BREAKOUT_PROVIDER_ID,
    OPENING_DRIVE_PROVIDER_ID,
    ORB_RETEST_PROVIDER_ID,
    TREND_PULLBACK_PROVIDER_ID,
    build_compression_trend_candidate_pool,
    compression_breakout_provider,
    opening_drive_provider,
    orb_retest_provider,
    register_compression_trend_providers,
    register_opening_drive_orb_providers,
    trend_pullback_provider,
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
    "COMPRESSION_BREAKOUT_PROVIDER_ID",
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
    "TREND_PULLBACK_PROVIDER_ID",
    "build_candidate_pool",
    "build_compression_trend_candidate_pool",
    "build_opening_drive_orb_candidate_pool",
    "candidate_from_mapping",
    "classify_movement_regime",
    "compression_breakout_provider",
    "opening_drive_provider",
    "orb_retest_provider",
    "register_compression_trend_providers",
    "register_opening_drive_orb_providers",
    "trend_pullback_provider",
    "validate_strategy_candidate",
]

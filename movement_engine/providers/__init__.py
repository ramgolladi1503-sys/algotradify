"""Movement strategy providers.

Providers produce StrategyCandidate objects only. They do not execute orders,
call brokers, mutate runtime state, or bypass the movement candidate pool.
"""

from movement_engine.providers.compression_trend import (
    COMPRESSION_BREAKOUT_PROVIDER_ID,
    TREND_PULLBACK_PROVIDER_ID,
    build_compression_trend_candidate_pool,
    compression_breakout_provider,
    register_compression_trend_providers,
    trend_pullback_provider,
)
from movement_engine.providers.opening_drive_orb import (
    OPENING_DRIVE_PROVIDER_ID,
    ORB_RETEST_PROVIDER_ID,
    opening_drive_provider,
    orb_retest_provider,
    register_opening_drive_orb_providers,
)

__all__ = [
    "COMPRESSION_BREAKOUT_PROVIDER_ID",
    "OPENING_DRIVE_PROVIDER_ID",
    "ORB_RETEST_PROVIDER_ID",
    "TREND_PULLBACK_PROVIDER_ID",
    "build_compression_trend_candidate_pool",
    "compression_breakout_provider",
    "opening_drive_provider",
    "orb_retest_provider",
    "register_compression_trend_providers",
    "register_opening_drive_orb_providers",
    "trend_pullback_provider",
]

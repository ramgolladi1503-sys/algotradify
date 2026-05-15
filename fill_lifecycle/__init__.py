"""Fill lifecycle normalization for Algotradify.

This package models order/fill evidence after a selected candidate becomes an
attempted trade. It does not submit orders and does not call broker APIs.
"""

from fill_lifecycle.lifecycle import (
    FillLifecycleEvent,
    FillLifecycleState,
    FillLifecycleStatus,
    normalize_fill_lifecycle,
)

__all__ = [
    "FillLifecycleEvent",
    "FillLifecycleState",
    "FillLifecycleStatus",
    "normalize_fill_lifecycle",
]

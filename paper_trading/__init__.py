"""Paper trading contracts for Algotradify.

This package builds simulation-only paper intent and lifecycle evidence. It does
not place broker orders and does not expose real order actions.
"""

from paper_trading.intent_bridge import (
    PaperOrderIntent,
    PaperOrderIntentResult,
    build_paper_order_intent,
    paper_order_intent_schema_contract,
    validate_paper_order_intent,
)
from paper_trading.lifecycle import (
    PaperOrderLifecycleEvent,
    PaperOrderLifecycleResult,
    PaperOrderLifecycleStatus,
    build_paper_order_lifecycle_event,
    paper_order_lifecycle_schema_contract,
    validate_paper_order_lifecycle_transition,
)

__all__ = [
    "PaperOrderIntent",
    "PaperOrderIntentResult",
    "build_paper_order_intent",
    "paper_order_intent_schema_contract",
    "validate_paper_order_intent",
    "PaperOrderLifecycleEvent",
    "PaperOrderLifecycleResult",
    "PaperOrderLifecycleStatus",
    "build_paper_order_lifecycle_event",
    "paper_order_lifecycle_schema_contract",
    "validate_paper_order_lifecycle_transition",
]

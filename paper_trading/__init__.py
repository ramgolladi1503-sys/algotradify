"""Paper trading contracts for Algotradify.

This package builds simulation-only paper intent, lifecycle, and fill evidence.
It does not place broker orders and does not expose real order actions.
"""

from paper_trading.fill_simulation import (
    PaperFillSimulationResult,
    PaperFillSimulationStatus,
    paper_fill_simulation_schema_contract,
    simulate_paper_fill,
    validate_paper_fill_simulation_inputs,
)
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
    "PaperFillSimulationResult",
    "PaperFillSimulationStatus",
    "paper_fill_simulation_schema_contract",
    "simulate_paper_fill",
    "validate_paper_fill_simulation_inputs",
]

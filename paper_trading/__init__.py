"""Paper trading contracts for Algotradify.

This package builds simulation-only paper intent, lifecycle, fill, position, and
MTM evidence. It does not place broker orders and does not expose real order
actions.
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
from paper_trading.mtm_pnl import (
    PaperMtmPnlResult,
    PaperMtmPnlStatus,
    build_paper_mtm_pnl,
    paper_mtm_pnl_schema_contract,
    validate_paper_mtm_pnl_inputs,
)
from paper_trading.position_ledger import (
    PaperPositionLedgerResult,
    PaperPositionLedgerStatus,
    build_paper_position_ledger,
    paper_position_ledger_schema_contract,
    validate_paper_position_ledger_inputs,
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
    "PaperPositionLedgerResult",
    "PaperPositionLedgerStatus",
    "build_paper_position_ledger",
    "paper_position_ledger_schema_contract",
    "validate_paper_position_ledger_inputs",
    "PaperMtmPnlResult",
    "PaperMtmPnlStatus",
    "build_paper_mtm_pnl",
    "paper_mtm_pnl_schema_contract",
    "validate_paper_mtm_pnl_inputs",
]

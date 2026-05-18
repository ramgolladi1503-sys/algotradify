"""Paper trading contracts for Algotradify.

This package builds simulation-only paper intent, lifecycle, fill, position, MTM,
realized PnL, slippage, performance snapshot, and canonical paper event journal
evidence. It does not place broker orders and does not expose real order actions.
"""

from paper_trading.event_journal import (
    PaperEventJournalResult,
    append_paper_event,
    load_paper_events,
    paper_event_journal_schema_contract,
)
from paper_trading.events import (
    PaperEvent,
    PaperEventType,
    normalize_paper_event,
    paper_event_schema_contract,
    validate_paper_event,
)
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
from paper_trading.performance_snapshot import (
    PaperPerformanceSnapshotResult,
    PaperPerformanceSnapshotStatus,
    build_paper_performance_snapshot,
    paper_performance_snapshot_schema_contract,
    validate_paper_performance_snapshot_inputs,
)
from paper_trading.position_ledger import (
    PaperPositionLedgerResult,
    PaperPositionLedgerStatus,
    build_paper_position_ledger,
    paper_position_ledger_schema_contract,
    validate_paper_position_ledger_inputs,
)
from paper_trading.realized_pnl import (
    PaperRealizedPnlResult,
    PaperRealizedPnlStatus,
    build_paper_realized_pnl,
    paper_realized_pnl_schema_contract,
    validate_paper_realized_pnl_inputs,
)
from paper_trading.slippage import (
    PaperSlippageResult,
    PaperSlippageStatus,
    build_paper_slippage_report,
    paper_slippage_schema_contract,
    validate_paper_slippage_inputs,
)

__all__ = [
    "PaperEvent",
    "PaperEventType",
    "PaperEventJournalResult",
    "append_paper_event",
    "load_paper_events",
    "normalize_paper_event",
    "paper_event_schema_contract",
    "paper_event_journal_schema_contract",
    "validate_paper_event",
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
    "PaperRealizedPnlResult",
    "PaperRealizedPnlStatus",
    "build_paper_realized_pnl",
    "paper_realized_pnl_schema_contract",
    "validate_paper_realized_pnl_inputs",
    "PaperSlippageResult",
    "PaperSlippageStatus",
    "build_paper_slippage_report",
    "paper_slippage_schema_contract",
    "validate_paper_slippage_inputs",
    "PaperPerformanceSnapshotResult",
    "PaperPerformanceSnapshotStatus",
    "build_paper_performance_snapshot",
    "paper_performance_snapshot_schema_contract",
    "validate_paper_performance_snapshot_inputs",
]

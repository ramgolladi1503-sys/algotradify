"""Paper trading contracts for Algotradify.

This package builds simulation-only paper intent evidence. It does not place
broker orders and does not expose real order actions.
"""

from paper_trading.intent_bridge import (
    PaperOrderIntent,
    PaperOrderIntentResult,
    build_paper_order_intent,
    paper_order_intent_schema_contract,
    validate_paper_order_intent,
)

__all__ = [
    "PaperOrderIntent",
    "PaperOrderIntentResult",
    "build_paper_order_intent",
    "paper_order_intent_schema_contract",
    "validate_paper_order_intent",
]

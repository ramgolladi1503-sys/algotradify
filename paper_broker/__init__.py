"""Synthetic PAPER broker adapter contracts.

This package creates paper-order acknowledgements only. It never calls Kite,
Upstox, or any real broker API.
"""

from paper_broker.adapter import (
    PaperBrokerExecutionResult,
    PaperBrokerOrderAck,
    execute_paper_order,
    validate_paper_order_intent,
)

__all__ = [
    "PaperBrokerExecutionResult",
    "PaperBrokerOrderAck",
    "execute_paper_order",
    "validate_paper_order_intent",
]

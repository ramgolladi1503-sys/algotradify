"""Pre-broker order intent contracts.

This package builds validated order-intent records only. It does not place,
modify, cancel, or exit broker orders.
"""

from order_intent.contract import (
    OrderIntent,
    OrderIntentBuildResult,
    build_order_intent,
    validate_order_intent_inputs,
)

__all__ = [
    "OrderIntent",
    "OrderIntentBuildResult",
    "build_order_intent",
    "validate_order_intent_inputs",
]

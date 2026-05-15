"""Execution safety contracts for Algotradify.

This package defines pre-order safety gates only. It does not place orders,
call broker APIs, or mutate broker/runtime state.
"""

from execution_safety.contract import (
    ExecutionMode,
    ExecutionSafetyDecision,
    ExecutionSafetyPolicy,
    evaluate_execution_safety,
)

__all__ = [
    "ExecutionMode",
    "ExecutionSafetyDecision",
    "ExecutionSafetyPolicy",
    "evaluate_execution_safety",
]

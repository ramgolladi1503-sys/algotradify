"""Unified execution readiness contract for Algotradify.

This package is the first layer allowed to say execution_allowed=true. It still
does not place orders.
"""

from execution_readiness.contract import (
    ExecutionReadiness,
    ExecutionReadinessStatus,
    RiskReadiness,
    build_execution_readiness,
)

__all__ = [
    "ExecutionReadiness",
    "ExecutionReadinessStatus",
    "RiskReadiness",
    "build_execution_readiness",
]

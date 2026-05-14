"""Opportunity Layer for Algotradify.

The Opportunity Layer tracks candidate survival through normalize -> classify ->
rank -> select -> emit. It does not execute trades and does not decide broker
readiness.
"""

from opportunity_layer.pipeline import (
    OpportunityLayerResult,
    OpportunityRecord,
    OpportunityStatus,
    run_opportunity_pipeline,
)

__all__ = [
    "OpportunityLayerResult",
    "OpportunityRecord",
    "OpportunityStatus",
    "run_opportunity_pipeline",
]

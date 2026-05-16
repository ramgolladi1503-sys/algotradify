"""Outcome logging and replay for Algotradify.

Outcome replay normalizes selected/blocked/filled/rejected evidence into an
auditable candidate history. It does not place orders or mutate broker state.
"""

from outcome_replay.query import filter_outcome_replay_records, replay_query_metadata
from outcome_replay.replay import (
    OutcomeEvent,
    OutcomeReplaySummary,
    OutcomeStatus,
    normalize_outcome_replay,
)

__all__ = [
    "OutcomeEvent",
    "OutcomeReplaySummary",
    "OutcomeStatus",
    "filter_outcome_replay_records",
    "normalize_outcome_replay",
    "replay_query_metadata",
]

"""Candidate Truth Layer for Algotradify.

This layer normalizes strategy drafts and runtime-shaped candidates into a strict
truth record. It classifies candidate provenance and shape. It does not decide
execution readiness and never marks a candidate executable.
"""

from candidate_truth.layer import (
    CandidateTruthRecord,
    CandidateTruthStatus,
    normalize_candidate,
    normalize_candidates,
)

__all__ = [
    "CandidateTruthRecord",
    "CandidateTruthStatus",
    "normalize_candidate",
    "normalize_candidates",
]

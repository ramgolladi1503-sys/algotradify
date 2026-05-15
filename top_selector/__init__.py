"""Top executable selector for Algotradify.

The selector chooses the best execution-allowed candidate from trade quality
ranking. It does not place orders and does not call broker APIs.
"""

from top_selector.selector import (
    TopExecutableSelection,
    TopExecutableSelectorStatus,
    select_top_executable,
)

__all__ = [
    "TopExecutableSelection",
    "TopExecutableSelectorStatus",
    "select_top_executable",
]

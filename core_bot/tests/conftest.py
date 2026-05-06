import sys
import os
import tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import after adjusting sys.path; core_bot uses absolute imports like `import core...`.
from core.lifecycle import stop_all as stop_lifecycle

# Force runtime writes outside the repo during tests (do not read stale local `.runtime`).
# Use a unique temp dir per test session to avoid cross-run contamination.
os.environ["DATA_ROOT"] = tempfile.mkdtemp(prefix="trading_bot_runtime_tests_")


@pytest.fixture(scope="session", autouse=True)
def _shutdown_managed_runtime_lifecycle():
    try:
        yield
    finally:
        # Explicit component stop first, then registered handles; safe to call repeatedly.
        stop_lifecycle(timeout=3.0, reason="pytest_teardown")

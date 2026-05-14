"""Compatibility wrapper for starting the Algotradify runtime.

`python main.py` is the canonical runtime command. This wrapper remains so older
scripts that call `python -m runner.live_wrapper` continue to work.
"""
from __future__ import annotations

import sys
import threading
import time
import traceback
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT_PATH = str(_REPO_ROOT)
if _REPO_ROOT_PATH not in sys.path:
    sys.path.insert(0, _REPO_ROOT_PATH)

from extensions.safe_emit import safe_emit


def heartbeat():
    while True:
        safe_emit("heartbeat", {"status": "alive"})
        time.sleep(2)


def start():
    try:
        from main import main as algotradify_main
    except Exception as exc:
        print("algotradify main import failed. Full traceback:", file=sys.stderr)
        traceback.print_exc()
        raise RuntimeError(f"Wrapper bootstrap failed: {type(exc).__name__}: {exc}") from exc

    t = threading.Thread(target=heartbeat, name="wrapper-heartbeat", daemon=True)
    t.start()
    print("Launching algotradify.main()")
    return algotradify_main()


if __name__ == "__main__":
    start()

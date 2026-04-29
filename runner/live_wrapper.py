import importlib
import sys
import threading
import time
import traceback
from pathlib import Path

# Support both `python -m runner.live_wrapper` and direct script execution
# (`python runner/live_wrapper.py`) by ensuring repo root is importable.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT_PATH = str(_REPO_ROOT)
if _REPO_ROOT_PATH not in sys.path:
    sys.path.insert(0, _REPO_ROOT_PATH)

from extensions.safe_emit import safe_emit


def _ensure_core_bot_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    core_bot_dir = repo_root / "core_bot"
    core_bot_path = str(core_bot_dir)
    if core_bot_dir.exists() and core_bot_path not in sys.path:
        # core_bot modules use absolute imports like "from config import ...".
        sys.path.insert(0, core_bot_path)


def _load_core_bot_main():
    _ensure_core_bot_on_path()
    return importlib.import_module("core_bot.main")


def _resolve_entrypoint(module):
    if hasattr(module, "main") and callable(module.main):
        return module.main, "main"
    if hasattr(module, "run") and callable(module.run):
        return module.run, "run"
    raise RuntimeError(
        f"No callable entrypoint found in {module.__name__}; expected main() or run()."
    )


def heartbeat():
    while True:
        safe_emit("heartbeat", {"status": "alive"})
        time.sleep(2)


def start():
    try:
        main_module = _load_core_bot_main()
        entry_fn, entry_name = _resolve_entrypoint(main_module)
    except Exception as exc:
        print("core_bot import failed. Full traceback:", file=sys.stderr)
        traceback.print_exc()
        raise RuntimeError(f"Wrapper bootstrap failed: {type(exc).__name__}: {exc}") from exc

    t = threading.Thread(target=heartbeat, name="wrapper-heartbeat", daemon=True)
    t.start()
    print(f"Launching {main_module.__name__}.{entry_name}()")
    entry_fn()


if __name__ == "__main__":
    start()

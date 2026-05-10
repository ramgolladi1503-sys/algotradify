import importlib
import importlib.util
import os
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


class TradebotCoreNotFound(RuntimeError):
    """Raised when algotradify cannot resolve a tradebot-compatible runtime."""


def _prepend_sys_path(path: Path) -> None:
    resolved = str(path.expanduser().resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def _is_tradebot_root(path: Path) -> bool:
    root = path.expanduser().resolve()
    return (root / "main.py").exists() and (root / "core").is_dir() and (root / "config").is_dir()


def _candidate_tradebot_roots() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("TRADEBOT_ROOT", "CORE_BOT_ROOT"):
        configured = os.getenv(env_name)
        if configured:
            candidates.append(Path(configured))

    candidates.extend(
        [
            _REPO_ROOT / "core_bot",
            _REPO_ROOT.parent / "tradebot",
            Path.home() / "tradebot",
        ]
    )

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        try:
            key = str(candidate.expanduser().resolve())
        except Exception:
            key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _resolve_tradebot_root() -> Path:
    for candidate in _candidate_tradebot_roots():
        if _is_tradebot_root(candidate):
            return candidate.expanduser().resolve()

    checked = "\n".join(f"  - {p.expanduser()}" for p in _candidate_tradebot_roots())
    raise TradebotCoreNotFound(
        "No tradebot-compatible core found. algotradify needs either an embedded "
        "core_bot/ copied from tradebot main, or TRADEBOT_ROOT pointing to a local "
        "tradebot checkout.\n\nChecked:\n"
        f"{checked}\n\nFix:\n"
        "  1. Run: python scripts/sync_tradebot_core.py --source ../tradebot\n"
        "     or\n"
        "  2. Export: TRADEBOT_ROOT=/absolute/path/to/tradebot\n"
        "Then rerun: python -m runner.live_wrapper"
    )


def _load_external_tradebot_main(root: Path):
    _prepend_sys_path(root)
    module_path = root / "main.py"
    spec = importlib.util.spec_from_file_location("tradebot_external_main", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load tradebot main module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_core_bot_main():
    tradebot_root = _resolve_tradebot_root()

    # Embedded/synced mode: core_bot is a package inside algotradify. The synced
    # tradebot main.py uses absolute imports like `from config import ...`, so
    # core_bot itself must be first on sys.path.
    embedded_core = (_REPO_ROOT / "core_bot").resolve()
    if tradebot_root == embedded_core and (embedded_core / "__init__.py").exists():
        _prepend_sys_path(embedded_core)
        return importlib.import_module("core_bot.main")

    # External mode: useful when tradebot is kept as a separate read-only checkout.
    return _load_external_tradebot_main(tradebot_root)


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
        print("tradebot core bootstrap failed. Full traceback:", file=sys.stderr)
        traceback.print_exc()
        raise RuntimeError(f"Wrapper bootstrap failed: {type(exc).__name__}: {exc}") from exc

    t = threading.Thread(target=heartbeat, name="wrapper-heartbeat", daemon=True)
    t.start()
    print(f"Launching {main_module.__name__}.{entry_name}()")
    entry_fn()


if __name__ == "__main__":
    start()

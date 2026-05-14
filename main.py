"""Algotradify runtime entrypoint.

This file intentionally starts the trading runtime, not the Streamlit dashboard.
The operator UI for this repo is the FastAPI + React stack:

  python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
  npm --prefix frontend run dev -- --host 0.0.0.0 --port 3000

The runtime engine is expected under ./core_bot after running:

  python scripts/sync_tradebot_core.py --source ../tradebot --force

A separate external checkout can still be used with TRADEBOT_ROOT, but the
preferred self-contained Algotradify path is ./core_bot.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from pathlib import Path
from types import ModuleType
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent
EMBEDDED_ENGINE_ROOT = REPO_ROOT / "core_bot"

# Make this repository importable for local helpers and keep the embedded engine
# importable for Tradebot-style absolute imports such as `from core...` and
# `from config import config as cfg`.
for candidate in (REPO_ROOT, EMBEDDED_ENGINE_ROOT):
    text = str(candidate.resolve())
    if text not in sys.path:
        sys.path.insert(0, text)


class AlgotradifyRuntimeNotFound(RuntimeError):
    """Raised when no Tradebot-compatible runtime can be loaded."""


def _is_tradebot_compatible_root(path: Path) -> bool:
    root = path.expanduser().resolve()
    return (root / "main.py").is_file() and (root / "core").is_dir() and (root / "config").is_dir()


def _candidate_runtime_roots() -> list[Path]:
    """Return runtime roots in the order Algotradify should try them.

    Embedded core comes first because this repo should be able to run on its own.
    TRADEBOT_ROOT/CORE_BOT_ROOT are still respected as explicit overrides for
    local development or verification against a separate checkout.
    """
    candidates: list[Path] = []

    for env_name in ("ALGOTRADIFY_ENGINE_ROOT", "TRADEBOT_ROOT", "CORE_BOT_ROOT"):
        configured = os.getenv(env_name)
        if configured:
            candidates.append(Path(configured))

    candidates.extend(
        [
            EMBEDDED_ENGINE_ROOT,
            REPO_ROOT.parent / "tradebot",
            Path.home() / "tradebot",
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            key = str(candidate.expanduser().resolve())
        except Exception:
            key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def resolve_runtime_root() -> Path:
    for candidate in _candidate_runtime_roots():
        if _is_tradebot_compatible_root(candidate):
            return candidate.expanduser().resolve()

    checked = "\n".join(f"  - {p.expanduser()}" for p in _candidate_runtime_roots())
    raise AlgotradifyRuntimeNotFound(
        "No Tradebot-compatible runtime was found for Algotradify.\n\n"
        "Expected a runtime root containing: main.py, core/, and config/.\n\n"
        f"Checked:\n{checked}\n\n"
        "Fix for self-contained Algotradify:\n"
        "  python scripts/sync_tradebot_core.py --source ../tradebot --force\n"
        "  python main.py\n\n"
        "Temporary external-checkout mode:\n"
        "  export TRADEBOT_ROOT=/absolute/path/to/tradebot\n"
        "  python main.py"
    )


def _load_runtime_main(runtime_root: Path) -> ModuleType:
    runtime_root = runtime_root.expanduser().resolve()
    runtime_root_text = str(runtime_root)
    if runtime_root_text not in sys.path:
        sys.path.insert(0, runtime_root_text)

    module_path = runtime_root / "main.py"
    spec = importlib.util.spec_from_file_location("algotradify_embedded_tradebot_main", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load runtime main module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_entrypoint(module: ModuleType) -> tuple[Callable[[], object], str]:
    for name in ("main", "run"):
        entrypoint = getattr(module, name, None)
        if callable(entrypoint):
            return entrypoint, name
    raise RuntimeError(f"No callable main() or run() found in {module.__name__}")


def main() -> object:
    """Start the embedded Tradebot runtime from inside Algotradify."""
    os.environ.setdefault("ALGOTRADIFY_UI_STACK", "fastapi_react")

    try:
        runtime_root = resolve_runtime_root()
        runtime_module = _load_runtime_main(runtime_root)
        entrypoint, entrypoint_name = _resolve_entrypoint(runtime_module)
    except Exception as exc:
        print("[ALGOTRADIFY_BOOT_ERROR] failed to bootstrap runtime", file=sys.stderr)
        traceback.print_exc()
        raise RuntimeError(f"Algotradify runtime bootstrap failed: {type(exc).__name__}: {exc}") from exc

    print(f"[ALGOTRADIFY_BOOT] repo_root={REPO_ROOT}")
    print(f"[ALGOTRADIFY_BOOT] runtime_root={runtime_root}")
    print("[ALGOTRADIFY_BOOT] ui_stack=FastAPI+React; Streamlit is not started by this entrypoint")
    print(f"[ALGOTRADIFY_BOOT] launching {runtime_module.__name__}.{entrypoint_name}()")
    return entrypoint()


run = main


if __name__ == "__main__":
    main()

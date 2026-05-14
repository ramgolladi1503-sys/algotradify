"""Algotradify runtime entrypoint.

This file intentionally starts the trading runtime, not the Streamlit dashboard.
The operator UI for this repo is the FastAPI + React stack:

  python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
  npm --prefix frontend run dev -- --host 0.0.0.0 --port 3000

The runtime engine is expected under ./core_bot after running:

  python scripts/sync_tradebot_core.py --source ../tradebot --force

A separate external checkout can still be used with ALGOTRADIFY_ENGINE_ROOT or
TRADEBOT_ROOT, but the preferred self-contained Algotradify path is ./core_bot.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from pathlib import Path
from types import ModuleType
from typing import Callable

from runtime_contract import candidate_runtime_roots, is_tradebot_compatible_root
from runtime_contract import resolve_runtime_root as _resolve_runtime_root

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
    return is_tradebot_compatible_root(path)


def _candidate_runtime_roots() -> list[Path]:
    return candidate_runtime_roots(base_repo_root=REPO_ROOT)


def resolve_runtime_root() -> Path:
    runtime_root = _resolve_runtime_root(base_repo_root=REPO_ROOT)
    if runtime_root is not None:
        return runtime_root

    checked = "\n".join(f"  - {p.expanduser()}" for p in _candidate_runtime_roots())
    raise AlgotradifyRuntimeNotFound(
        "No Tradebot-compatible runtime was found for Algotradify.\n\n"
        "Expected a runtime root containing: main.py, core/, and config/.\n\n"
        f"Checked:\n{checked}\n\n"
        "Fix for self-contained Algotradify:\n"
        "  python scripts/sync_tradebot_core.py --source ../tradebot --force\n"
        "  python main.py\n\n"
        "Temporary external-checkout mode:\n"
        "  export ALGOTRADIFY_ENGINE_ROOT=/absolute/path/to/tradebot\n"
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

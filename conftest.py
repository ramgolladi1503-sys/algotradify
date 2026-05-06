import sys
from pathlib import Path


# Allow running `pytest` from repo root while the engine is vendored under `core_bot/`
# with absolute imports like `import core...`.
_CORE_BOT_DIR = (Path(__file__).resolve().parent / "core_bot").resolve()
if _CORE_BOT_DIR.exists():
    core_bot_path = str(_CORE_BOT_DIR)
    if core_bot_path not in sys.path:
        sys.path.insert(0, core_bot_path)


import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonStateStore:
    def __init__(self, path: str = "runtime/state.json"):
        self.path = Path(os.getenv("ALGOTRADIFY_STATE_FILE", path))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            backup = self.path.with_suffix(f".corrupt.{int(datetime.now(timezone.utc).timestamp())}.json")
            try:
                self.path.rename(backup)
            except Exception:
                pass
            return {"_load_error": str(exc), "_backup": str(backup)}

    def save(self, state: dict[str, Any]) -> None:
        payload = dict(state)
        payload["saved_at"] = datetime.now(timezone.utc).isoformat()
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        tmp.replace(self.path)

    def info(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "exists": self.path.exists(),
            "size_bytes": self.path.stat().st_size if self.path.exists() else 0,
        }

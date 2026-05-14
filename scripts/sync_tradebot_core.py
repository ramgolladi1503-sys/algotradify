#!/usr/bin/env python3
"""
Sync tradebot main into algotradify/core_bot without touching tradebot.

Usage:
  python scripts/sync_tradebot_core.py --source ../tradebot
  python scripts/sync_tradebot_core.py --source /absolute/path/to/tradebot --force

This is intentionally local-first. It does not clone, mutate, or push tradebot.
It copies a read-only source checkout into algotradify/core_bot and preserves
algotradify's frontend/API/runtime bridge files.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = REPO_ROOT / "core_bot"

EXCLUDE_PATTERNS = {
    ".git",
    ".git/*",
    ".github/workflows/*",
    ".venv",
    ".venv/*",
    "venv",
    "venv/*",
    "__pycache__",
    "__pycache__/*",
    "*.pyc",
    ".pytest_cache",
    ".pytest_cache/*",
    ".mypy_cache",
    ".mypy_cache/*",
    ".ruff_cache",
    ".ruff_cache/*",
    ".runtime",
    ".runtime/*",
    "runtime",
    "runtime/*",
    "logs",
    "logs/*",
    "data/*.csv",
    "data/*.parquet",
    "data/*.db",
    "data/*.sqlite",
    "data/*.sqlite3",
    "*.log",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    ".env",
    ".env.*",
    "kite_access_token",
    "*.token",
    "*.secret",
}

REQUIRED_SOURCE_MARKERS = ["main.py", "core", "config"]


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _excluded(rel_path: str) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in EXCLUDE_PATTERNS)


def _git_value(source: Path, args: list[str]) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(source), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or None
    except Exception:
        return None


def _validate_source(source: Path) -> None:
    missing = [item for item in REQUIRED_SOURCE_MARKERS if not (source / item).exists()]
    if missing:
        raise SystemExit(
            f"Source does not look like tradebot main. Missing: {', '.join(missing)}\n"
            f"source={source}"
        )


def _clean_target(target: Path, force: bool) -> None:
    if target.exists() and not force:
        raise SystemExit(
            f"Target already exists: {target}\n"
            "Use --force to replace it, or set ALGOTRADIFY_ENGINE_ROOT/TRADEBOT_ROOT to a separate checkout instead."
        )
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def _copy_tree(source: Path, target: Path) -> int:
    copied = 0
    for path in source.rglob("*"):
        rel = _rel(path, source)
        if _excluded(rel):
            continue
        if any(_excluded(part) for part in rel.split("/")):
            continue
        dest = target / rel
        if path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        copied += 1
    return copied


def _write_package_marker(target: Path) -> None:
    marker = target / "__init__.py"
    if not marker.exists():
        marker.write_text(
            '"""Embedded tradebot runtime synced into algotradify.\n\n'
            'Do not hand-edit copied core code here. Re-sync from tradebot main.\n'
            '"""\n',
            encoding="utf-8",
        )


def _write_source_metadata(source: Path, target: Path, copied_files: int) -> None:
    metadata = {
        "source_path": str(source),
        "source_remote": _git_value(source, ["config", "--get", "remote.origin.url"]),
        "source_branch": _git_value(source, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "source_commit": _git_value(source, ["rev-parse", "HEAD"]),
        "synced_at_utc": datetime.now(timezone.utc).isoformat(),
        "copied_files": copied_files,
        "excluded_patterns": sorted(EXCLUDE_PATTERNS),
    }
    (target / "TRADEBOT_SOURCE.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _ensure_gitignore() -> None:
    gitignore = REPO_ROOT / ".gitignore"
    lines = []
    if gitignore.exists():
        lines = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
    required = [
        "core_bot/.runtime/",
        "core_bot/runtime/",
        "core_bot/logs/",
        "core_bot/.env",
        "core_bot/.env.*",
        "core_bot/**/*.token",
        "core_bot/**/*.secret",
        "core_bot/data/*.csv",
        "core_bot/data/*.parquet",
        "core_bot/data/*.db",
        "core_bot/data/*.sqlite*",
    ]
    updated = list(lines)
    for item in required:
        if item not in updated:
            updated.append(item)
    if updated != lines:
        gitignore.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync tradebot main into algotradify/core_bot")
    parser.add_argument("--source", required=True, help="Path to a local tradebot checkout on main")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="Target directory, default core_bot")
    parser.add_argument("--force", action="store_true", help="Replace existing target directory")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()

    _validate_source(source)
    _clean_target(target, force=args.force)
    copied_files = _copy_tree(source, target)
    _write_package_marker(target)
    _write_source_metadata(source, target, copied_files)
    _ensure_gitignore()

    print(f"Synced tradebot core into {target}")
    print(f"Copied files: {copied_files}")
    print("Next checks:")
    print("  python main.py")
    print("  python -m runner.live_wrapper")
    print("  python -m uvicorn api.server:app --host 0.0.0.0 --port 8000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

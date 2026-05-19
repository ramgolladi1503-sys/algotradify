#!/usr/bin/env python3
"""Plan a native Tradebot source import without copying files.

Runtime Correction PR 2 is planning-only. This script inspects a source checkout
and target repository, reports required markers, planned import candidates,
excluded patterns, and collisions. It intentionally does not copy, delete,
rename, or modify files.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_SOURCE_MARKERS = ("main.py", "core", "config")
ROOT_FILE_CANDIDATES = ("main.py", "run_live.sh", "run_all.sh", "requirements.txt")
DIRECTORY_CANDIDATES = ("core", "config", "strategies", "dashboard", "ml", "models", "rl", "fixtures")
OPTIONAL_SCRIPT_CANDIDATES = (
    "scripts/kite_autologin_localhost.py",
    "scripts/start_depth_ws.py",
    "scripts/scheduler.py",
)

EXCLUDE_PATTERNS = (
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
    "*.token",
    "*.secret",
    "kite_access_token",
)

PROTECTED_TARGET_PREFIXES = (
    "api/",
    "frontend/",
    "paper_trading/",
    "agent_system/",
    "execution_safety/",
    "execution_readiness/",
    "movement_engine/",
    "top_selector/",
)

SAFE_FLAGS = {
    "read_only": True,
    "planning_only": True,
    "source_imported": False,
    "runtime_behavior_changed": False,
    "is_order_action": False,
    "broker_api_called": False,
    "real_order_id": None,
    "live_mode_touched": False,
}


@dataclass(frozen=True)
class PathPlan:
    path: str
    source_exists: bool
    target_exists: bool
    kind: str
    action: str
    decision_required: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "path": self.path,
            "source_exists": self.source_exists,
            "target_exists": self.target_exists,
            "kind": self.kind,
            "action": self.action,
            "decision_required": self.decision_required,
        }
        if self.reason:
            payload["reason"] = self.reason
        return payload


def _is_excluded(rel_path: str) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in EXCLUDE_PATTERNS)


def _protected_target_collision(rel_path: str) -> bool:
    return any(rel_path == prefix.rstrip("/") or rel_path.startswith(prefix) for prefix in PROTECTED_TARGET_PREFIXES)


def _path_kind(path: Path) -> str:
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "missing"


def _git_value(source: Path, args: list[str]) -> str | None:
    try:
        value = subprocess.check_output(
            ["git", "-C", str(source), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return value or None
    except Exception:
        return None


def _marker_status(source: Path) -> dict[str, bool]:
    return {marker: (source / marker).exists() for marker in REQUIRED_SOURCE_MARKERS}


def _plan_path(source: Path, target: Path, rel_path: str, *, action: str) -> PathPlan:
    source_path = source / rel_path
    target_path = target / rel_path
    source_exists = source_path.exists()
    target_exists = target_path.exists()
    kind = _path_kind(source_path)

    if not source_exists:
        return PathPlan(
            path=rel_path,
            source_exists=False,
            target_exists=target_exists,
            kind="missing",
            action="skip_missing_source",
            reason="SOURCE_PATH_MISSING",
        )
    if _is_excluded(rel_path):
        return PathPlan(
            path=rel_path,
            source_exists=True,
            target_exists=target_exists,
            kind=kind,
            action="exclude",
            reason="EXCLUDED_PATTERN",
        )
    if _protected_target_collision(rel_path):
        return PathPlan(
            path=rel_path,
            source_exists=True,
            target_exists=target_exists,
            kind=kind,
            action="blocked_protected_target",
            decision_required=True,
            reason="PROTECTED_TARGET_PREFIX",
        )
    if target_exists:
        reason = "TARGET_COLLISION"
        planned_action = "defer_collision"
        if rel_path == "main.py":
            reason = "ROOT_MAIN_PROMOTION_DEFERRED_TO_RUNTIME_CORRECTION_PR5"
        elif rel_path.startswith("scripts/"):
            reason = "SCRIPT_IMPORT_REQUIRES_CURATED_DECISION"
        return PathPlan(
            path=rel_path,
            source_exists=True,
            target_exists=True,
            kind=kind,
            action=planned_action,
            decision_required=True,
            reason=reason,
        )
    return PathPlan(
        path=rel_path,
        source_exists=True,
        target_exists=False,
        kind=kind,
        action=action,
        decision_required=False,
    )


def _candidate_scripts(source: Path) -> list[str]:
    scripts_root = source / "scripts"
    candidates = [path for path in OPTIONAL_SCRIPT_CANDIDATES if (source / path).exists()]
    if scripts_root.is_dir():
        for child in sorted(scripts_root.iterdir()):
            if child.is_file() and child.suffix in {".py", ".sh"}:
                rel = child.relative_to(source).as_posix()
                if rel not in candidates:
                    candidates.append(rel)
    return candidates


def build_tradebot_native_import_plan(source: str | Path | None, target: str | Path | None = None) -> dict[str, Any]:
    source_root = Path(source).expanduser().resolve() if source is not None else None
    target_root = Path(target or ".").expanduser().resolve()

    blockers: list[str] = []
    warnings: list[str] = []

    if source_root is None:
        blockers.append("SOURCE_REQUIRED")
        markers = {marker: False for marker in REQUIRED_SOURCE_MARKERS}
        source_exists = False
    else:
        source_exists = source_root.exists()
        if not source_exists:
            blockers.append("SOURCE_PATH_MISSING")
            markers = {marker: False for marker in REQUIRED_SOURCE_MARKERS}
        else:
            markers = _marker_status(source_root)
            missing_markers = [marker for marker, present in markers.items() if not present]
            if missing_markers:
                blockers.extend(f"SOURCE_REQUIRED_MARKER_MISSING:{marker}" for marker in missing_markers)

    if not target_root.exists():
        blockers.append("TARGET_PATH_MISSING")

    root_file_plans: list[PathPlan] = []
    directory_plans: list[PathPlan] = []
    script_plans: list[PathPlan] = []

    if source_root is not None and source_exists and target_root.exists():
        root_file_plans = [
            _plan_path(source_root, target_root, rel_path, action="plan_root_file_import")
            for rel_path in ROOT_FILE_CANDIDATES
        ]
        directory_plans = [
            _plan_path(source_root, target_root, rel_path, action="plan_directory_import")
            for rel_path in DIRECTORY_CANDIDATES
        ]
        script_plans = [
            _plan_path(source_root, target_root, rel_path, action="defer_curated_script_import")
            for rel_path in _candidate_scripts(source_root)
        ]

    all_plans = root_file_plans + directory_plans + script_plans
    collisions = [plan.to_dict() for plan in all_plans if plan.target_exists or plan.decision_required]
    protected_collisions = [plan.to_dict() for plan in all_plans if plan.reason == "PROTECTED_TARGET_PREFIX"]
    unresolved_decisions = [plan.to_dict() for plan in all_plans if plan.decision_required]

    if unresolved_decisions:
        blockers.append("UNRESOLVED_IMPORT_DECISIONS")
    if protected_collisions:
        blockers.append("PROTECTED_TARGET_COLLISIONS")
    if not script_plans and source_root is not None and source_exists:
        warnings.append("NO_OPTIONAL_SCRIPT_CANDIDATES_FOUND")

    safe_to_import = not blockers and not unresolved_decisions

    return {
        "contract": "tradebot_native_import_plan_v1",
        "source_path": str(source_root) if source_root is not None else None,
        "target_path": str(target_root),
        "source_exists": source_exists,
        "source_repo_valid": bool(source_exists and all(markers.values())),
        "required_source_markers": markers,
        "source_git": {
            "remote": _git_value(source_root, ["config", "--get", "remote.origin.url"]) if source_root and source_exists else None,
            "branch": _git_value(source_root, ["rev-parse", "--abbrev-ref", "HEAD"]) if source_root and source_exists else None,
            "commit": _git_value(source_root, ["rev-parse", "HEAD"]) if source_root and source_exists else None,
        },
        "planned_import": {
            "root_files": [plan.to_dict() for plan in root_file_plans],
            "directories": [plan.to_dict() for plan in directory_plans],
            "candidate_scripts": [plan.to_dict() for plan in script_plans],
        },
        "excluded_patterns": list(EXCLUDE_PATTERNS),
        "protected_target_prefixes": list(PROTECTED_TARGET_PREFIXES),
        "collisions": collisions,
        "protected_collisions": protected_collisions,
        "unresolved_decisions": unresolved_decisions,
        "safe_to_import": safe_to_import,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        **SAFE_FLAGS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan native Tradebot import without copying files")
    parser.add_argument("--source", required=True, help="Path to local Tradebot checkout")
    parser.add_argument("--target", default=".", help="Target algotradify checkout")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    payload = build_tradebot_native_import_plan(args.source, args.target)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"source_repo_valid={payload['source_repo_valid']}")
        print(f"safe_to_import={payload['safe_to_import']}")
        if payload["blockers"]:
            print("blockers=" + ",".join(payload["blockers"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

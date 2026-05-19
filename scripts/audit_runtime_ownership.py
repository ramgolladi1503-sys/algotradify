#!/usr/bin/env python3
"""Read-only runtime ownership audit for algotradify.

This script intentionally does not import runtime modules, start the bot, create
runtime directories, call broker APIs, or mutate files. It inspects source files
and path markers only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ENGINE_ROOT_ENV_VARS = ("ALGOTRADIFY_ENGINE_ROOT", "TRADEBOT_ROOT", "CORE_BOT_ROOT")
DEFAULT_FALLBACK_LABELS = ("./core_bot", "../tradebot", "~/tradebot")
SAFE_FLAGS = {
    "read_only": True,
    "audit_only": True,
    "is_order_action": False,
    "broker_api_called": False,
    "real_order_id": None,
    "live_mode_touched": False,
}


def _repo_root(start: Path | None = None) -> Path:
    return (start or Path(__file__).resolve().parents[1]).expanduser().resolve()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _is_wrapper_main(main_text: str) -> bool:
    wrapper_markers = (
        "spec_from_file_location",
        "_load_runtime_main",
        "resolve_runtime_root()",
        "ALGOTRADIFY_BOOT",
        "Tradebot-compatible runtime",
        "runtime_root = resolve_runtime_root()",
    )
    return any(marker in main_text for marker in wrapper_markers)


def _external_fallbacks_present(runtime_contract_text: str) -> bool:
    fallback_markers = ("root.parent / \"tradebot\"", "home_root / \"tradebot\"", "../tradebot", "~/tradebot")
    return any(marker in runtime_contract_text for marker in fallback_markers)


def _path_info(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }


def build_runtime_ownership_audit(repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve() if repo_root is not None else _repo_root()
    main_path = root / "main.py"
    runtime_contract_path = root / "runtime_contract.py"
    main_text = _read_text(main_path)
    runtime_contract_text = _read_text(runtime_contract_path)

    root_has_core = (root / "core").is_dir()
    root_has_config = (root / "config").is_dir()
    root_has_strategies = (root / "strategies").is_dir()
    root_main_exists = main_path.is_file()
    root_main_is_wrapper = _is_wrapper_main(main_text)
    external_fallbacks_enabled = _external_fallbacks_present(runtime_contract_text)
    core_bot_main = root / "core_bot" / "main.py"
    core_bot_runtime_present = core_bot_main.is_file() and (root / "core_bot" / "core").is_dir() and (root / "core_bot" / "config").is_dir()
    native_runtime_present = root_main_exists and root_has_core and root_has_config and not root_main_is_wrapper

    if native_runtime_present and not external_fallbacks_enabled:
        runtime_ownership = "NATIVE"
    elif native_runtime_present:
        runtime_ownership = "NATIVE_WITH_EXTERNAL_COMPATIBILITY"
    else:
        runtime_ownership = "WRAPPER_OR_EXTERNAL_COMPATIBLE"

    blockers: list[str] = []
    if not root_main_exists:
        blockers.append("ROOT_MAIN_MISSING")
    if root_main_is_wrapper:
        blockers.append("ROOT_MAIN_IS_RUNTIME_LAUNCHER_WRAPPER")
    if not root_has_core:
        blockers.append("ROOT_CORE_DIRECTORY_MISSING")
    if not root_has_config:
        blockers.append("ROOT_CONFIG_DIRECTORY_MISSING")
    if external_fallbacks_enabled:
        blockers.append("EXTERNAL_RUNTIME_FALLBACKS_ENABLED")

    warnings: list[str] = []
    if core_bot_runtime_present:
        warnings.append("CORE_BOT_RUNTIME_PRESENT_BUT_NOT_PROOF_OF_NATIVE_ROOT_OWNERSHIP")
    if root_has_strategies and not native_runtime_present:
        warnings.append("STRATEGIES_PRESENT_WITHOUT_COMPLETE_NATIVE_RUNTIME_CONTRACT")

    return {
        "contract": "runtime_ownership_audit_v1",
        "runtime_ownership": runtime_ownership,
        "native_runtime_present": native_runtime_present,
        "root_has_main": root_main_exists,
        "root_main_is_wrapper": root_main_is_wrapper,
        "root_has_core": root_has_core,
        "root_has_config": root_has_config,
        "root_has_strategies": root_has_strategies,
        "core_bot_runtime_present": core_bot_runtime_present,
        "external_fallbacks_enabled": external_fallbacks_enabled,
        "normal_feature_prs_should_pause": runtime_ownership != "NATIVE",
        "safe_to_continue_feature_prs": runtime_ownership == "NATIVE",
        "repo_root": str(root),
        "checked_paths": {
            "root_main": _path_info(main_path),
            "root_core": _path_info(root / "core"),
            "root_config": _path_info(root / "config"),
            "root_strategies": _path_info(root / "strategies"),
            "core_bot_main": _path_info(core_bot_main),
            "runtime_contract": _path_info(runtime_contract_path),
        },
        "runtime_resolution_inputs": {
            "env_vars": list(ENGINE_ROOT_ENV_VARS),
            "default_fallbacks": list(DEFAULT_FALLBACK_LABELS),
        },
        "blockers": blockers,
        "warnings": warnings,
        **SAFE_FLAGS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit algotradify runtime ownership without changing behavior")
    parser.add_argument("--repo-root", default=None, help="Repository root to inspect; defaults to current repo")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    payload = build_runtime_ownership_audit(args.repo_root)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"runtime_ownership={payload['runtime_ownership']}")
        print(f"native_runtime_present={payload['native_runtime_present']}")
        print(f"normal_feature_prs_should_pause={payload['normal_feature_prs_should_pause']}")
        if payload["blockers"]:
            print("blockers=" + ",".join(payload["blockers"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

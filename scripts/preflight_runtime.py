#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Support direct execution from scripts/ without requiring package install.
REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT_TEXT = str(REPO_ROOT)
if REPO_ROOT_TEXT not in sys.path:
    sys.path.insert(0, REPO_ROOT_TEXT)

from runtime_contract import run_preflight


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Algotradify runtime preflight checks")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full preflight result as JSON",
    )
    parser.add_argument(
        "--no-create-runtime-dirs",
        action="store_true",
        help="Do not create runtime artifact directories while checking writability",
    )
    args = parser.parse_args()

    result = run_preflight(
        base_repo_root=REPO_ROOT,
        create_runtime_dirs=not args.no_create_runtime_dirs,
    )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Runtime preflight: {result['status']}")
        print(f"Runtime root: {result.get('runtime_root') or 'unresolved'}")
        print(f"Runtime artifact root: {result.get('runtime_artifact_root') or 'unresolved'}")
        summary = result.get("summary") or {}
        print(
            "Summary: "
            f"PASS={summary.get('pass_count', 0)} "
            f"WARN={summary.get('warn_count', 0)} "
            f"FAIL={summary.get('fail_count', 0)}"
        )
        for check in result.get("checks", []):
            status = check.get("status", "UNKNOWN")
            name = check.get("name", "unknown")
            message = check.get("message", "")
            print(f"[{status}] {name}: {message}")

    return 0 if result.get("status") in {"PASS", "WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

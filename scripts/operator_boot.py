#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> int:
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    return subprocess.call(cmd, cwd=REPO_ROOT, env=merged_env)


def _preflight() -> int:
    return _run([
        sys.executable,
        str(REPO_ROOT / "scripts" / "preflight_runtime.py"),
        "--json",
        "--no-create-runtime-dirs",
    ], env={"ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME": "true"})


def _sim() -> int:
    return _run([sys.executable, str(REPO_ROOT / "main.py")], env={"EXECUTION_MODE": "SIM", "TRADING_MODE": "SIM", "ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME": "true"})


def _paper() -> int:
    return _run([sys.executable, str(REPO_ROOT / "main.py")], env={"EXECUTION_MODE": "PAPER", "TRADING_MODE": "PAPER", "ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME": "true"})


def _ui_api(host: str, port: int) -> int:
    return _run([
        sys.executable,
        "-m",
        "uvicorn",
        "api.server:app",
        "--host",
        host,
        "--port",
        str(port),
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe Algotradify operator boot commands")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", help="Run native runtime preflight only")
    sub.add_parser("sim", help="Start native main.py in SIM mode")
    sub.add_parser("paper", help="Start native main.py in PAPER mode")
    api = sub.add_parser("ui-api", help="Start FastAPI operator API only")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "preflight":
        return _preflight()
    if args.command == "sim":
        return _sim()
    if args.command == "paper":
        return _paper()
    if args.command == "ui-api":
        return _ui_api(args.host, args.port)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

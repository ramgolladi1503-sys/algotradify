from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_LIVE = ROOT / "run_live.sh"
OPERATOR_BOOT = ROOT / "scripts" / "operator_boot.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_run_live_exists_and_is_guarded_live_entrypoint():
    text = _text(RUN_LIVE)

    assert text.startswith("#!/usr/bin/env bash")
    assert "--start requires --i-understand-live-risk" in text
    assert "DRY_RUN=true is incompatible with LIVE startup" in text
    assert 'export TRADING_MODE="LIVE"' in text
    assert 'export EXECUTION_MODE="LIVE"' in text
    assert "exec python \"$ROOT_DIR/main.py\"" in text


def test_run_live_does_not_default_to_start():
    text = _text(RUN_LIVE)

    assert "selected_count=$((START + VALIDATE_ONLY + LOGIN_ONLY))" in text
    assert "choose exactly one of --validate-only, --login-only, or --start" in text
    assert "CONFIRM_LIVE=0" in text
    assert "--i-understand-live-risk" in text


def test_run_live_keeps_auth_local_and_does_not_add_api_or_ui_behavior():
    text = _text(RUN_LIVE)

    assert "scripts/kite_autologin_localhost.py" in text
    assert "uvicorn" not in text
    assert "frontend" not in text
    assert "agent" not in text.lower()
    assert "paper_trading" not in text


def test_operator_boot_cli_exposes_safe_modes_without_live_start():
    text = _text(OPERATOR_BOOT)

    assert "sub.add_parser(\"preflight\"" in text
    assert "sub.add_parser(\"sim\"" in text
    assert "sub.add_parser(\"paper\"" in text
    assert "sub.add_parser(\"ui-api\"" in text
    assert '"EXECUTION_MODE": "SIM"' in text
    assert '"TRADING_MODE": "SIM"' in text
    assert '"EXECUTION_MODE": "PAPER"' in text
    assert '"TRADING_MODE": "PAPER"' in text
    assert '"EXECUTION_MODE": "LIVE"' not in text
    assert '"TRADING_MODE": "LIVE"' not in text


def test_operator_boot_cli_uses_native_runtime_preflight():
    text = _text(OPERATOR_BOOT)

    assert "preflight_runtime.py" in text
    assert '"ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME": "true"' in text


def test_run_live_has_no_forbidden_artifact_patterns():
    forbidden = [".env", "*.token", "*.secret", "*.sqlite", "*.db", "__pycache__"]
    text = _text(RUN_LIVE)
    for marker in forbidden:
        assert marker not in text


def test_operator_scripts_are_not_world_writable():
    for path in (RUN_LIVE, OPERATOR_BOOT):
        mode = path.stat().st_mode
        assert not (mode & 0o002), f"world-writable operator script: {path}"

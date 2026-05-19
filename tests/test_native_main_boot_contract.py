from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"


def _main_text() -> str:
    return MAIN.read_text(encoding="utf-8", errors="ignore")


def test_root_main_no_longer_uses_dynamic_external_loader():
    text = _main_text()

    assert "importlib.util.spec_from_file_location" not in text
    assert "_load_runtime_main" not in text
    assert "Algotradify runtime bootstrap failed" not in text
    assert "resolve_runtime_root()" not in text


def test_root_main_preserves_native_tradebot_startup_imports():
    text = _main_text()

    required_markers = [
        "import core.runtime_guard",
        "from config import config as cfg",
        "from core.orchestrator import Orchestrator",
        "from core.readiness_gate import run_readiness_check",
        "from core.security_guard import enforce_startup_security",
        "from core.instance_lock import InstanceLock",
        "from core.db_guard import ensure_db_ready",
        "from core.trade_log_paths import ensure_trade_log_exists",
        "from core.broker_truth_reconciler import BrokerTruthReconciler",
        "from core.auth import validate_kite_startup_credentials",
    ]
    for marker in required_markers:
        assert marker in text


def test_root_main_preserves_safety_critical_startup_calls():
    text = _main_text()

    required_calls = [
        "_validate_runtime_mode_config_alignment(exec_mode)",
        "_ensure_runtime_dirs(repo_root)",
        "_repair_events_log_if_needed()",
        "validate_kite_startup_credentials(",
        "InstanceLock(repo_root_path=repo_root)",
        "ensure_db_ready()",
        "enforce_startup_security(repo_root=repo_root, require_token=True)",
        "ensure_trade_log_exists()",
        "auto_clear_risk_halt_if_safe()",
        "run_readiness_check(write_log=True)",
        "Orchestrator(",
        "orchestrator.live_monitoring()",
    ]
    for call in required_calls:
        assert call in text


def test_root_main_preserves_run_alias_and_module_entrypoint():
    tree = ast.parse(_main_text())
    assigned_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned_names.add(target.id)

    assert "run" in assigned_names
    assert "if __name__ == \"__main__\":" in _main_text()


def test_root_run_live_not_promoted_in_pr5():
    assert not (ROOT / "run_live.sh").exists()
    assert (ROOT / "runtime_native" / "tradebot_run_live.sh").is_file()

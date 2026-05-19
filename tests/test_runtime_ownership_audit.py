from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.audit_runtime_ownership import build_runtime_ownership_audit


def _write_wrapper_repo(root: Path) -> None:
    (root / "main.py").write_text(
        "import importlib.util\n"
        "def resolve_runtime_root():\n"
        "    return None\n"
        "def _load_runtime_main(runtime_root):\n"
        "    return importlib.util.spec_from_file_location('x', runtime_root / 'main.py')\n",
        encoding="utf-8",
    )
    (root / "runtime_contract.py").write_text(
        "def candidate_runtime_roots(root, home_root):\n"
        "    return [root / 'core_bot', root.parent / 'tradebot', home_root / 'tradebot']\n",
        encoding="utf-8",
    )


def _write_native_repo(root: Path, *, external_fallback: bool = False) -> None:
    (root / "main.py").write_text("def main():\n    return 'native'\n", encoding="utf-8")
    (root / "core").mkdir()
    (root / "config").mkdir()
    (root / "strategies").mkdir()
    runtime_contract = "def candidate_runtime_roots():\n    return [repo_root()]\n"
    if external_fallback:
        runtime_contract += "# legacy fallback: root.parent / \"tradebot\"\n"
    (root / "runtime_contract.py").write_text(runtime_contract, encoding="utf-8")


def test_runtime_ownership_audit_detects_current_wrapper_or_external_compatible_repo():
    payload = build_runtime_ownership_audit(Path(__file__).resolve().parents[1])

    assert payload["contract"] == "runtime_ownership_audit_v1"
    assert payload["runtime_ownership"] in {
        "WRAPPER_OR_EXTERNAL_COMPATIBLE",
        "NATIVE_WITH_EXTERNAL_COMPATIBILITY",
        "NATIVE",
    }
    assert payload["read_only"] is True
    assert payload["audit_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["live_mode_touched"] is False
    assert "ALGOTRADIFY_ENGINE_ROOT" in payload["runtime_resolution_inputs"]["env_vars"]


def test_runtime_ownership_audit_flags_wrapper_and_external_fallbacks(tmp_path):
    _write_wrapper_repo(tmp_path)

    payload = build_runtime_ownership_audit(tmp_path)

    assert payload["runtime_ownership"] == "WRAPPER_OR_EXTERNAL_COMPATIBLE"
    assert payload["native_runtime_present"] is False
    assert payload["root_main_is_wrapper"] is True
    assert payload["external_fallbacks_enabled"] is True
    assert payload["normal_feature_prs_should_pause"] is True
    assert payload["safe_to_continue_feature_prs"] is False
    assert "ROOT_MAIN_IS_RUNTIME_LAUNCHER_WRAPPER" in payload["blockers"]
    assert "ROOT_CORE_DIRECTORY_MISSING" in payload["blockers"]
    assert "ROOT_CONFIG_DIRECTORY_MISSING" in payload["blockers"]
    assert "EXTERNAL_RUNTIME_FALLBACKS_ENABLED" in payload["blockers"]


def test_runtime_ownership_audit_detects_native_runtime(tmp_path):
    _write_native_repo(tmp_path)

    payload = build_runtime_ownership_audit(tmp_path)

    assert payload["runtime_ownership"] == "NATIVE"
    assert payload["native_runtime_present"] is True
    assert payload["root_main_is_wrapper"] is False
    assert payload["root_has_core"] is True
    assert payload["root_has_config"] is True
    assert payload["external_fallbacks_enabled"] is False
    assert payload["normal_feature_prs_should_pause"] is False
    assert payload["safe_to_continue_feature_prs"] is True
    assert payload["blockers"] == []


def test_runtime_ownership_audit_detects_native_with_external_compatibility(tmp_path):
    _write_native_repo(tmp_path, external_fallback=True)

    payload = build_runtime_ownership_audit(tmp_path)

    assert payload["runtime_ownership"] == "NATIVE_WITH_EXTERNAL_COMPATIBILITY"
    assert payload["native_runtime_present"] is True
    assert payload["external_fallbacks_enabled"] is True
    assert payload["normal_feature_prs_should_pause"] is True
    assert "EXTERNAL_RUNTIME_FALLBACKS_ENABLED" in payload["blockers"]


def test_runtime_ownership_audit_cli_outputs_json():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/audit_runtime_ownership.py", "--repo-root", str(repo_root), "--json"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["contract"] == "runtime_ownership_audit_v1"
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False


def test_runtime_ownership_audit_does_not_mutate_runtime_dirs(tmp_path):
    _write_wrapper_repo(tmp_path)
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    build_runtime_ownership_audit(tmp_path)

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert after == before

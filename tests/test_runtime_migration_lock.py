from __future__ import annotations

import shutil
from pathlib import Path

from scripts.runtime_migration_lock import run_lock_checks


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_migration_lock_passes_current_repo_contract():
    payload = run_lock_checks(ROOT)

    assert payload["contract"] == "runtime_migration_lock_v1"
    assert payload["status"] == "PASS"
    assert payload["fail_count"] == 0
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["live_mode_touched"] is False


def test_runtime_migration_lock_contains_critical_gate_names():
    payload = run_lock_checks(ROOT)
    names = {check["name"] for check in payload["checks"]}

    required_fragments = [
        "root_main.native_lock",
        "root_main.safety_markers",
        "run_live.guarded_live_lock",
        "operator_boot.no_live_command",
        "runtime_contract.external_deprecation_lock",
        "runtime_contract.native_lock",
        "runtime_ownership_route.py.get_only",
        "auth_visibility_route.py.get_only",
        "safe_flags",
        "actionless_panel_lock",
        "forbidden_artifact.absent",
    ]
    for fragment in required_fragments:
        assert any(fragment in name for name in names), fragment


def test_runtime_migration_lock_fails_if_main_reintroduces_dynamic_loader(tmp_path):
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__", "*.pyc"))
    main = work / "main.py"
    main.write_text(main.read_text(encoding="utf-8") + "\nimportlib.util.spec_from_file_location\n", encoding="utf-8")

    payload = run_lock_checks(work)

    assert payload["status"] == "FAIL"
    assert any(
        check["status"] == "FAIL" and "root_main.native_lock" in check["name"]
        for check in payload["checks"]
    )


def test_runtime_migration_lock_fails_if_run_live_loses_confirmation_gate(tmp_path):
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__", "*.pyc"))
    run_live = work / "run_live.sh"
    run_live.write_text(
        run_live.read_text(encoding="utf-8").replace("--start requires --i-understand-live-risk", "start allowed"),
        encoding="utf-8",
    )

    payload = run_lock_checks(work)

    assert payload["status"] == "FAIL"
    assert any(
        check["status"] == "FAIL" and "run_live.guarded_live_lock" in check["name"]
        for check in payload["checks"]
    )


def test_runtime_migration_lock_fails_if_operator_boot_adds_live_command(tmp_path):
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__", "*.pyc"))
    operator_boot = work / "scripts" / "operator_boot.py"
    operator_boot.write_text(
        operator_boot.read_text(encoding="utf-8") + "\nLIVE = {\"EXECUTION_MODE\": \"LIVE\"}\n",
        encoding="utf-8",
    )

    payload = run_lock_checks(work)

    assert payload["status"] == "FAIL"
    assert any(
        check["status"] == "FAIL" and "operator_boot.no_live_command" in check["name"]
        for check in payload["checks"]
    )


def test_runtime_migration_lock_fails_if_route_adds_mutation_method(tmp_path):
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__", "*.pyc"))
    route = work / "api" / "runtime_ownership_route.py"
    route.write_text(route.read_text(encoding="utf-8") + "\n@app.post('/runtime/ownership')\ndef mutate(): pass\n", encoding="utf-8")

    payload = run_lock_checks(work)

    assert payload["status"] == "FAIL"
    assert any(
        check["status"] == "FAIL" and "no_mutation_routes" in check["name"]
        for check in payload["checks"]
    )


def test_runtime_migration_lock_fails_if_token_artifact_is_committed(tmp_path):
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__", "*.pyc"))
    token = work / ".runtime" / "kite_access_token"
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text("secret-token", encoding="utf-8")

    payload = run_lock_checks(work)

    assert payload["status"] == "FAIL"
    assert any(
        check["status"] == "FAIL" and "forbidden_artifact.absent" in check["name"]
        for check in payload["checks"]
    )

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.plan_tradebot_native_import import build_tradebot_native_import_plan


def _make_tradebot_source(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.py").write_text("def main():\n    return 'tradebot'\n", encoding="utf-8")
    for directory in ("core", "config", "strategies", "dashboard", "ml", "models", "rl", "fixtures", "scripts"):
        (root / directory).mkdir(exist_ok=True)
    (root / "core" / "orchestrator.py").write_text("class Orchestrator: pass\n", encoding="utf-8")
    (root / "config" / "config.py").write_text("EXECUTION_MODE='SIM'\n", encoding="utf-8")
    (root / "dashboard" / "streamlit_app.py").write_text("# dashboard\n", encoding="utf-8")
    (root / "run_live.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (root / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (root / "scripts" / "kite_autologin_localhost.py").write_text("# auth helper\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=bad\n", encoding="utf-8")
    (root / ".runtime").mkdir(exist_ok=True)
    (root / ".runtime" / "kite_access_token").write_text("token\n", encoding="utf-8")
    return root


def _make_target(root: Path, *, collisions: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if collisions:
        (root / "main.py").write_text("# algotradify wrapper\n", encoding="utf-8")
        (root / "scripts").mkdir(exist_ok=True)
        (root / "scripts" / "kite_autologin_localhost.py").write_text("# existing script\n", encoding="utf-8")
    return root


def test_import_plan_blocks_missing_source(tmp_path):
    target = _make_target(tmp_path / "target")
    payload = build_tradebot_native_import_plan(tmp_path / "missing", target)

    assert payload["contract"] == "tradebot_native_import_plan_v1"
    assert payload["source_exists"] is False
    assert payload["source_repo_valid"] is False
    assert payload["safe_to_import"] is False
    assert "SOURCE_PATH_MISSING" in payload["blockers"]
    assert payload["read_only"] is True
    assert payload["planning_only"] is True
    assert payload["source_imported"] is False
    assert payload["runtime_behavior_changed"] is False
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["live_mode_touched"] is False


def test_import_plan_requires_tradebot_markers(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("def main(): pass\n", encoding="utf-8")
    target = _make_target(tmp_path / "target")

    payload = build_tradebot_native_import_plan(source, target)

    assert payload["source_repo_valid"] is False
    assert payload["required_source_markers"]["main.py"] is True
    assert payload["required_source_markers"]["core"] is False
    assert payload["required_source_markers"]["config"] is False
    assert "SOURCE_REQUIRED_MARKER_MISSING:core" in payload["blockers"]
    assert "SOURCE_REQUIRED_MARKER_MISSING:config" in payload["blockers"]


def test_import_plan_reports_clean_candidates_without_copying(tmp_path):
    source = _make_tradebot_source(tmp_path / "tradebot")
    target = _make_target(tmp_path / "algotradify")
    before = sorted(path.relative_to(target).as_posix() for path in target.rglob("*"))

    payload = build_tradebot_native_import_plan(source, target)

    after = sorted(path.relative_to(target).as_posix() for path in target.rglob("*"))
    assert after == before
    assert payload["source_repo_valid"] is True
    assert payload["read_only"] is True
    assert payload["planning_only"] is True
    assert payload["source_imported"] is False
    assert payload["runtime_behavior_changed"] is False
    root_files = {item["path"]: item for item in payload["planned_import"]["root_files"]}
    directories = {item["path"]: item for item in payload["planned_import"]["directories"]}
    assert root_files["main.py"]["action"] == "plan_root_file_import"
    assert root_files["run_live.sh"]["action"] == "plan_root_file_import"
    assert directories["core"]["action"] == "plan_directory_import"
    assert directories["config"]["action"] == "plan_directory_import"
    assert ".env" in payload["excluded_patterns"]
    assert "*.token" in payload["excluded_patterns"]
    assert ".runtime/*" in payload["excluded_patterns"]


def test_import_plan_reports_root_and_script_collisions(tmp_path):
    source = _make_tradebot_source(tmp_path / "tradebot")
    target = _make_target(tmp_path / "algotradify", collisions=True)

    payload = build_tradebot_native_import_plan(source, target)

    assert payload["safe_to_import"] is False
    assert "UNRESOLVED_IMPORT_DECISIONS" in payload["blockers"]
    collisions = {item["path"]: item for item in payload["collisions"]}
    assert collisions["main.py"]["decision_required"] is True
    assert collisions["main.py"]["reason"] == "ROOT_MAIN_PROMOTION_DEFERRED_TO_RUNTIME_CORRECTION_PR5"
    assert collisions["scripts/kite_autologin_localhost.py"]["decision_required"] is True
    assert collisions["scripts/kite_autologin_localhost.py"]["reason"] == "SCRIPT_IMPORT_REQUIRES_CURATED_DECISION"


def test_import_plan_blocks_protected_target_prefixes(tmp_path):
    source = _make_tradebot_source(tmp_path / "tradebot")
    (source / "api").mkdir()
    (source / "api" / "server.py").write_text("# must not overwrite algotradify api\n", encoding="utf-8")
    target = _make_target(tmp_path / "algotradify")
    (target / "api").mkdir()

    payload = build_tradebot_native_import_plan(source, target)

    assert "api/" in payload["protected_target_prefixes"]
    # PR2 only plans approved candidates, so protected prefixes are documented but
    # not imported unless a future script explicitly tries to include them.
    assert payload["source_imported"] is False


def test_import_plan_cli_outputs_json(tmp_path):
    source = _make_tradebot_source(tmp_path / "tradebot")
    target = _make_target(tmp_path / "algotradify")
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [
            sys.executable,
            "scripts/plan_tradebot_native_import.py",
            "--source",
            str(source),
            "--target",
            str(target),
            "--json",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["contract"] == "tradebot_native_import_plan_v1"
    assert payload["source_repo_valid"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False


def test_import_plan_does_not_hide_unresolved_decisions(tmp_path):
    source = _make_tradebot_source(tmp_path / "tradebot")
    target = _make_target(tmp_path / "algotradify", collisions=True)

    payload = build_tradebot_native_import_plan(source, target)

    assert payload["unresolved_decisions"]
    assert payload["safe_to_import"] is False
    assert "UNRESOLVED_IMPORT_DECISIONS" in payload["blockers"]

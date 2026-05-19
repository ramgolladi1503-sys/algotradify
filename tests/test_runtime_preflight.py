from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from runtime_contract import run_preflight


def _write_file(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_runtime_root(path: Path, *, requirements: bool = True) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "main.py").write_text("def main():\n    return 'ok'\n", encoding="utf-8")
    (path / "core").mkdir(exist_ok=True)
    (path / "config").mkdir(exist_ok=True)
    if requirements:
        (path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    return path.resolve()


def _make_native_runtime_root(path: Path, *, requirements: bool = True) -> Path:
    root = _make_runtime_root(path, requirements=requirements)
    _write_file(root / "RUNTIME_SOURCE_MANIFEST.json", "{}\n")
    _write_file(root / "runtime_native" / "tradebot_main.py", "def main(): pass\n")
    return root


def _clear_runtime_env(monkeypatch) -> None:
    for name in (
        "ALGOTRADIFY_ENGINE_ROOT",
        "TRADEBOT_ROOT",
        "CORE_BOT_ROOT",
        "CORE_BOT_RUNTIME_ROOT",
        "ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME",
        "ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME",
        "EXECUTION_MODE",
        "TRADING_MODE",
    ):
        monkeypatch.delenv(name, raising=False)


def _check_map(result: dict) -> dict[str, dict]:
    return {check["name"]: check for check in result["checks"]}


def test_preflight_fails_when_no_runtime_root_exists(tmp_path, monkeypatch):
    _clear_runtime_env(monkeypatch)
    repo_root = tmp_path / "algotradify"
    repo_root.mkdir()
    home = tmp_path / "home"
    home.mkdir()

    result = run_preflight(base_repo_root=repo_root, home=home, create_runtime_dirs=False)

    assert result["status"] == "FAIL"
    assert result["runtime_root"] is None
    assert result["external_runtime_allowed"] is False
    assert result["external_runtime_deprecated"] is True
    checks = _check_map(result)
    assert checks["runtime_root.resolved"]["status"] == "FAIL"
    assert "checked_paths" in checks["runtime_root.resolved"]["metadata"]


def test_preflight_warns_for_missing_token_in_sim_mode(tmp_path, monkeypatch):
    _clear_runtime_env(monkeypatch)
    repo_root = _make_native_runtime_root(tmp_path / "algotradify")

    result = run_preflight(base_repo_root=repo_root, create_runtime_dirs=True)

    assert result["status"] == "WARN"
    assert result["runtime_root"] == str(repo_root)
    assert result["external_runtime_allowed"] is False
    checks = _check_map(result)
    assert checks["external_runtime_fallback.deprecated"]["status"] == "PASS"
    assert checks["runtime_root.main.py"]["status"] == "PASS"
    assert checks["runtime_root.core"]["status"] == "PASS"
    assert checks["runtime_root.config"]["status"] == "PASS"
    assert checks["runtime_root.requirements.txt"]["status"] == "PASS"
    assert checks["runtime_artifact_root.exists"]["status"] == "PASS"
    assert checks["runtime_artifact_root.writable"]["status"] == "PASS"
    assert checks["broker_token.available"]["status"] == "WARN"
    assert checks["execution_mode.valid"]["status"] == "PASS"


def test_preflight_fails_for_invalid_execution_mode(tmp_path, monkeypatch):
    _clear_runtime_env(monkeypatch)
    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    monkeypatch.setenv("EXECUTION_MODE", "DANGEROUS")

    result = run_preflight(base_repo_root=repo_root, create_runtime_dirs=True)

    assert result["status"] == "FAIL"
    checks = _check_map(result)
    assert checks["execution_mode.valid"]["status"] == "FAIL"


def test_preflight_requires_token_for_paper_or_live(tmp_path, monkeypatch):
    _clear_runtime_env(monkeypatch)
    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    monkeypatch.setenv("EXECUTION_MODE", "PAPER")

    result = run_preflight(base_repo_root=repo_root, create_runtime_dirs=True)

    assert result["status"] == "FAIL"
    checks = _check_map(result)
    assert checks["broker_token.available"]["status"] == "FAIL"


def test_preflight_passes_for_paper_when_token_candidate_exists(tmp_path, monkeypatch):
    _clear_runtime_env(monkeypatch)
    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    artifact_root = repo_root / ".runtime"
    artifact_root.mkdir(parents=True)
    (artifact_root / "kite_access_token").write_text("token", encoding="utf-8")
    monkeypatch.setenv("EXECUTION_MODE", "PAPER")

    result = run_preflight(base_repo_root=repo_root, create_runtime_dirs=True)

    assert result["status"] == "PASS"
    checks = _check_map(result)
    assert checks["broker_token.available"]["status"] == "PASS"


def test_runtime_preflight_api_returns_contract_payload(tmp_path, monkeypatch):
    server = importlib.import_module("api.server")
    client = TestClient(server.app)
    _clear_runtime_env(monkeypatch)

    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    monkeypatch.setattr(server, "_repo_root", lambda: repo_root)

    response = client.get("/runtime/preflight")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "WARN"
    assert payload["runtime_root"] == str(repo_root)
    assert payload["external_runtime_allowed"] is False
    assert payload["external_runtime_deprecated"] is True
    assert payload["checked_at_source"] == "runtime_contract.run_preflight"
    assert isinstance(payload["checks"], list)
    assert payload["summary"]["warn_count"] >= 1


def test_legacy_core_bot_preflight_requires_explicit_external_opt_in(tmp_path, monkeypatch):
    _clear_runtime_env(monkeypatch)
    repo_root = tmp_path / "algotradify"
    runtime_root = _make_runtime_root(repo_root / "core_bot")

    result_without_opt_in = run_preflight(base_repo_root=repo_root, create_runtime_dirs=False)
    assert result_without_opt_in["status"] == "FAIL"
    assert result_without_opt_in["runtime_root"] is None

    monkeypatch.setenv("ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME", "true")
    result_with_opt_in = run_preflight(base_repo_root=repo_root, create_runtime_dirs=False)

    assert result_with_opt_in["status"] == "WARN"
    assert result_with_opt_in["runtime_root"] == str(runtime_root)
    assert result_with_opt_in["external_runtime_allowed"] is True
    assert result_with_opt_in["external_runtime_used"] is True
    checks = _check_map(result_with_opt_in)
    assert checks["external_runtime_fallback.deprecated"]["status"] == "WARN"

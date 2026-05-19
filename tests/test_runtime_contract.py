from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


def _write_file(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_runtime_root(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "main.py").write_text("def main():\n    return 'ok'\n", encoding="utf-8")
    (path / "core").mkdir(exist_ok=True)
    (path / "config").mkdir(exist_ok=True)
    return path.resolve()


def _make_native_runtime_root(path: Path) -> Path:
    root = _make_runtime_root(path)
    _write_file(root / "requirements.txt", "pytest\n")
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
    ):
        monkeypatch.delenv(name, raising=False)


def test_api_uses_native_repo_root_by_default_after_external_fallback_deprecation(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    external_root = _make_runtime_root(tmp_path / "tradebot")
    home_dir = tmp_path / "home"
    _make_runtime_root(home_dir / "tradebot")

    monkeypatch.setattr(server, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    assert contract.external_runtime_allowed() is False
    assert contract.resolve_runtime_root(base_repo_root=repo_root) == repo_root
    assert server._tradebot_root() == repo_root
    assert external_root != server._tradebot_root()


def test_explicit_external_runtime_opt_in_still_temporarily_works(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    algotradify_root = _make_runtime_root(tmp_path / "algotradify_engine")
    tradebot_root = _make_runtime_root(tmp_path / "tradebot_engine")
    core_bot_root = _make_runtime_root(tmp_path / "core_bot_engine")

    monkeypatch.setattr(server, "_repo_root", lambda: repo_root)
    monkeypatch.setenv("ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME", "true")
    monkeypatch.setenv("ALGOTRADIFY_ENGINE_ROOT", str(algotradify_root))
    monkeypatch.setenv("TRADEBOT_ROOT", str(tradebot_root))
    monkeypatch.setenv("CORE_BOT_ROOT", str(core_bot_root))

    assert contract.external_runtime_allowed() is True
    assert contract.resolve_runtime_root(base_repo_root=repo_root) == repo_root

    assert contract.resolve_runtime_root(base_repo_root=repo_root, include_native_root=False) == algotradify_root
    assert server._tradebot_root() == repo_root

    monkeypatch.delenv("ALGOTRADIFY_ENGINE_ROOT")
    assert contract.resolve_runtime_root(base_repo_root=repo_root, include_native_root=False) == tradebot_root

    monkeypatch.delenv("TRADEBOT_ROOT")
    assert contract.resolve_runtime_root(base_repo_root=repo_root, include_native_root=False) == core_bot_root


def test_external_env_roots_ignored_by_default_even_when_configured(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)

    repo_root = tmp_path / "algotradify"
    repo_root.mkdir()
    external_root = _make_runtime_root(tmp_path / "tradebot_engine")
    monkeypatch.setenv("TRADEBOT_ROOT", str(external_root))

    assert contract.resolve_runtime_root(base_repo_root=repo_root) is None
    candidates = [candidate.expanduser().resolve() for candidate in contract.candidate_runtime_roots(base_repo_root=repo_root)]
    assert external_root not in candidates


def test_strict_native_mode_blocks_explicit_external_runtime_for_api(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    external_root = _make_runtime_root(tmp_path / "tradebot_engine")
    monkeypatch.setattr(server, "_repo_root", lambda: repo_root)
    monkeypatch.setenv("ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME", "true")
    monkeypatch.setenv("ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME", "true")
    monkeypatch.setenv("TRADEBOT_ROOT", str(external_root))

    assert contract.resolve_runtime_root(base_repo_root=repo_root) == repo_root
    assert server._tradebot_root() == repo_root
    assert contract.external_runtime_allowed() is False


def test_preflight_reports_external_fallback_deprecation_metadata(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)
    repo_root = _make_native_runtime_root(tmp_path / "algotradify")

    result = contract.run_preflight(base_repo_root=repo_root, create_runtime_dirs=False)

    assert result["external_runtime_allowed"] is False
    assert result["external_runtime_deprecated"] is True
    assert "deprecated" in result["external_runtime_deprecation_message"]
    assert any(
        check["name"] == "external_runtime_fallback.deprecated"
        and check["status"] == "PASS"
        and check["metadata"]["deprecated"] is True
        for check in result["checks"]
    )


def test_core_bot_runtime_root_override_wins_for_api_runtime_artifacts(tmp_path, monkeypatch):
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    runtime_artifact_root = tmp_path / "runtime_artifacts"
    runtime_artifact_root.mkdir()
    monkeypatch.setenv("CORE_BOT_RUNTIME_ROOT", str(runtime_artifact_root))

    assert server._runtime_root() == runtime_artifact_root.resolve()


def test_live_wrapper_delegates_to_algotradify_main_without_importing_real_runtime(monkeypatch):
    live_wrapper = importlib.import_module("runner.live_wrapper")

    calls: list[str] = []
    fake_main_module = types.ModuleType("main")

    def fake_main():
        calls.append("main_called")
        return "started"

    fake_main_module.main = fake_main

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            calls.append("heartbeat_started")

    monkeypatch.setitem(sys.modules, "main", fake_main_module)
    monkeypatch.setattr(live_wrapper.threading, "Thread", DummyThread)

    assert live_wrapper.start() == "started"
    assert calls == ["heartbeat_started", "main_called"]

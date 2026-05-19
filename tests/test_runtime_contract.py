from __future__ import annotations

import importlib
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


def test_api_uses_native_repo_root_by_default_after_main_promotion(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    external_root = _make_runtime_root(tmp_path / "tradebot")
    home_dir = tmp_path / "home"
    _make_runtime_root(home_dir / "tradebot")

    monkeypatch.setattr(server, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(contract, "repo_root", lambda: repo_root)
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    assert contract.resolve_runtime_root(base_repo_root=repo_root) == repo_root
    assert server._tradebot_root() == repo_root
    assert external_root != server._tradebot_root()


def test_api_and_contract_honor_explicit_external_runtime_when_allowed(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    algotradify_root = _make_runtime_root(tmp_path / "algotradify_engine")
    tradebot_root = _make_runtime_root(tmp_path / "tradebot_engine")
    core_bot_root = _make_runtime_root(tmp_path / "core_bot_engine")

    monkeypatch.setattr(server, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(contract, "repo_root", lambda: repo_root)
    monkeypatch.setenv("ALGOTRADIFY_ENGINE_ROOT", str(algotradify_root))
    monkeypatch.setenv("TRADEBOT_ROOT", str(tradebot_root))
    monkeypatch.setenv("CORE_BOT_ROOT", str(core_bot_root))

    assert contract.resolve_runtime_root(base_repo_root=repo_root) == algotradify_root
    assert server._tradebot_root() == algotradify_root

    monkeypatch.delenv("ALGOTRADIFY_ENGINE_ROOT")
    assert contract.resolve_runtime_root(base_repo_root=repo_root) == tradebot_root
    assert server._tradebot_root() == tradebot_root

    monkeypatch.delenv("TRADEBOT_ROOT")
    assert contract.resolve_runtime_root(base_repo_root=repo_root) == core_bot_root
    assert server._tradebot_root() == core_bot_root


def test_strict_native_mode_blocks_explicit_external_runtime_for_api(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    repo_root = _make_native_runtime_root(tmp_path / "algotradify")
    external_root = _make_runtime_root(tmp_path / "tradebot_engine")
    monkeypatch.setattr(server, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(contract, "repo_root", lambda: repo_root)
    monkeypatch.setenv("ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME", "true")
    monkeypatch.setenv("TRADEBOT_ROOT", str(external_root))

    assert contract.resolve_runtime_root(base_repo_root=repo_root) == repo_root
    assert server._tradebot_root() == repo_root


def test_core_bot_runtime_root_override_wins_for_api_runtime_artifacts(tmp_path, monkeypatch):
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    runtime_artifact_root = tmp_path / "runtime_artifacts"
    runtime_artifact_root.mkdir()
    monkeypatch.setenv("CORE_BOT_RUNTIME_ROOT", str(runtime_artifact_root))

    assert server._runtime_root() == runtime_artifact_root.resolve()


def test_live_wrapper_delegates_to_algotradify_main(monkeypatch):
    runtime_main = importlib.import_module("main")
    live_wrapper = importlib.import_module("runner.live_wrapper")

    calls: list[str] = []

    def fake_main():
        calls.append("main_called")
        return "started"

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            calls.append("heartbeat_started")

    monkeypatch.setattr(runtime_main, "main", fake_main)
    monkeypatch.setattr(live_wrapper.threading, "Thread", DummyThread)

    assert live_wrapper.start() == "started"
    assert calls == ["heartbeat_started", "main_called"]

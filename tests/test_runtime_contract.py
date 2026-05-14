from __future__ import annotations

import importlib
from pathlib import Path


def _make_runtime_root(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "main.py").write_text("def main():\n    return 'ok'\n", encoding="utf-8")
    (path / "core").mkdir(exist_ok=True)
    (path / "config").mkdir(exist_ok=True)
    return path.resolve()


def _clear_runtime_env(monkeypatch) -> None:
    for name in (
        "ALGOTRADIFY_ENGINE_ROOT",
        "TRADEBOT_ROOT",
        "CORE_BOT_ROOT",
        "CORE_BOT_RUNTIME_ROOT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_main_and_api_share_explicit_runtime_root_priority(tmp_path, monkeypatch):
    runtime_main = importlib.import_module("main")
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    algotradify_root = _make_runtime_root(tmp_path / "algotradify_engine")
    tradebot_root = _make_runtime_root(tmp_path / "tradebot_engine")
    core_bot_root = _make_runtime_root(tmp_path / "core_bot_engine")

    monkeypatch.setenv("ALGOTRADIFY_ENGINE_ROOT", str(algotradify_root))
    monkeypatch.setenv("TRADEBOT_ROOT", str(tradebot_root))
    monkeypatch.setenv("CORE_BOT_ROOT", str(core_bot_root))

    assert runtime_main.resolve_runtime_root() == algotradify_root
    assert server._tradebot_root() == algotradify_root

    monkeypatch.delenv("ALGOTRADIFY_ENGINE_ROOT")
    assert runtime_main.resolve_runtime_root() == tradebot_root
    assert server._tradebot_root() == tradebot_root

    monkeypatch.delenv("TRADEBOT_ROOT")
    assert runtime_main.resolve_runtime_root() == core_bot_root
    assert server._tradebot_root() == core_bot_root


def test_main_and_api_share_default_runtime_root_priority(tmp_path, monkeypatch):
    runtime_main = importlib.import_module("main")
    server = importlib.import_module("api.server")
    _clear_runtime_env(monkeypatch)

    repo_root = tmp_path / "algotradify"
    embedded_root = _make_runtime_root(repo_root / "core_bot")
    sibling_root = _make_runtime_root(tmp_path / "tradebot")
    home_dir = tmp_path / "home"
    home_root = _make_runtime_root(home_dir / "tradebot")

    monkeypatch.setattr(runtime_main, "REPO_ROOT", repo_root)
    monkeypatch.setattr(runtime_main, "EMBEDDED_ENGINE_ROOT", embedded_root)
    monkeypatch.setattr(server, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    assert runtime_main.resolve_runtime_root() == embedded_root
    assert server._tradebot_root() == embedded_root

    # Remove embedded marker first; both should fall through to ../tradebot.
    (embedded_root / "main.py").unlink()
    assert runtime_main.resolve_runtime_root() == sibling_root
    assert server._tradebot_root() == sibling_root

    # Remove sibling marker next; both should fall through to ~/tradebot.
    (sibling_root / "main.py").unlink()
    assert runtime_main.resolve_runtime_root() == home_root
    assert server._tradebot_root() == home_root


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

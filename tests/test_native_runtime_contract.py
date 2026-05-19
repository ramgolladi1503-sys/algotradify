from __future__ import annotations

import importlib
from pathlib import Path


def _write_file(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_native_source_root(path: Path, *, wrapper_main: bool = True) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    main_text = (
        "import importlib.util\n"
        "def resolve_runtime_root():\n"
        "    return None\n"
        "def _load_runtime_main(runtime_root):\n"
        "    return importlib.util.spec_from_file_location('x', runtime_root / 'main.py')\n"
        if wrapper_main
        else "def main():\n    return 'native'\n"
    )
    _write_file(path / "main.py", main_text)
    (path / "core").mkdir(exist_ok=True)
    (path / "config").mkdir(exist_ok=True)
    _write_file(path / "requirements.txt", "pytest\n")
    _write_file(path / "RUNTIME_SOURCE_MANIFEST.json", "{}\n")
    _write_file(path / "runtime_native" / "tradebot_main.py", "def main(): pass\n")
    return path.resolve()


def _make_external_runtime(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _write_file(path / "main.py", "def main(): return 'external'\n")
    (path / "core").mkdir(exist_ok=True)
    (path / "config").mkdir(exist_ok=True)
    _write_file(path / "requirements.txt", "pytest\n")
    return path.resolve()


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


def test_native_runtime_source_root_detected_with_pending_main_promotion(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)
    root = _make_native_source_root(tmp_path / "algotradify", wrapper_main=True)

    assert contract.is_native_runtime_source_root(root) is True
    assert contract.runtime_ownership_for_root(root) == "NATIVE_SOURCE_IMPORTED_PENDING_MAIN_PROMOTION"


def test_native_runtime_ownership_becomes_native_only_after_main_promotion(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)
    root = _make_native_source_root(tmp_path / "algotradify", wrapper_main=False)

    assert contract.runtime_ownership_for_root(root) == "NATIVE"


def test_strict_native_runtime_resolves_repo_root_without_external_fallback(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)
    root = _make_native_source_root(tmp_path / "algotradify", wrapper_main=True)
    external = _make_external_runtime(tmp_path / "tradebot")
    monkeypatch.setenv("ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME", "true")
    monkeypatch.setenv("TRADEBOT_ROOT", str(external))

    assert contract.resolve_runtime_root(base_repo_root=root) == root
    candidates = contract.candidate_runtime_roots(base_repo_root=root)
    assert root in [candidate.expanduser().resolve() for candidate in candidates]
    assert external not in [candidate.expanduser().resolve() for candidate in candidates]


def test_strict_native_runtime_fails_closed_when_native_markers_missing(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)
    root = tmp_path / "algotradify"
    root.mkdir()
    external = _make_external_runtime(tmp_path / "tradebot")
    monkeypatch.setenv("ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME", "true")
    monkeypatch.setenv("TRADEBOT_ROOT", str(external))

    assert contract.resolve_runtime_root(base_repo_root=root) is None
    result = contract.run_preflight(base_repo_root=root, create_runtime_dirs=False)
    assert result["status"] == "FAIL"
    assert result["native_required"] is True
    assert result["native_source_present"] is False
    assert result["external_runtime_used"] is False
    assert any(check["name"] == "native_runtime_source.present" and check["status"] == "FAIL" for check in result["checks"])


def test_preflight_reports_native_source_pending_main_promotion(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)
    root = _make_native_source_root(tmp_path / "algotradify", wrapper_main=True)
    monkeypatch.setenv("ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME", "true")

    result = contract.run_preflight(base_repo_root=root, create_runtime_dirs=False)

    assert result["status"] == "WARN"
    assert result["runtime_root"] == str(root)
    assert result["runtime_artifact_root"] == str((root / ".runtime").resolve())
    assert result["runtime_ownership"] == "NATIVE_SOURCE_IMPORTED_PENDING_MAIN_PROMOTION"
    assert result["native_required"] is True
    assert result["native_source_present"] is True
    assert result["native_main_promoted"] is False
    assert result["external_runtime_used"] is False
    assert any(check["name"] == "native_runtime_main.promoted" and check["status"] == "WARN" for check in result["checks"])


def test_default_runtime_resolution_preserves_wrapper_behavior_until_pr5(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)
    root = _make_native_source_root(tmp_path / "algotradify", wrapper_main=True)
    embedded = _make_external_runtime(root / "core_bot")

    assert contract.resolve_runtime_root(base_repo_root=root) == embedded
    result = contract.run_preflight(base_repo_root=root, create_runtime_dirs=False)
    assert result["runtime_root"] == str(embedded)
    assert result["external_runtime_used"] is True
    assert result["runtime_ownership"] == "NATIVE_SOURCE_IMPORTED_PENDING_MAIN_PROMOTION"


def test_external_fallback_can_be_disabled_without_requiring_native(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)
    root = tmp_path / "algotradify"
    root.mkdir()
    _make_external_runtime(tmp_path / "tradebot")
    monkeypatch.setenv("ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME", "false")

    assert contract.resolve_runtime_root(base_repo_root=root) is None
    candidates = [candidate.expanduser().resolve() for candidate in contract.candidate_runtime_roots(base_repo_root=root)]
    assert (tmp_path / "tradebot").resolve() not in candidates


def test_runtime_artifact_root_uses_repo_runtime_for_native_source(tmp_path, monkeypatch):
    contract = importlib.import_module("runtime_contract")
    _clear_runtime_env(monkeypatch)
    root = _make_native_source_root(tmp_path / "algotradify", wrapper_main=True)

    assert contract.runtime_artifact_root(engine_root=root, base_repo_root=root) == (root / ".runtime").resolve()

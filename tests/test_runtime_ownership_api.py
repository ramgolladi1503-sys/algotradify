from __future__ import annotations

from pathlib import Path

from api.runtime_ownership import build_runtime_ownership_payload
from api.runtime_ownership_route import install_runtime_ownership_route


def _write_file(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_native_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _write_file(root / "main.py", "def main():\n    return 'native'\n")
    (root / "core").mkdir(exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    _write_file(root / "requirements.txt", "pytest\n")
    _write_file(root / "RUNTIME_SOURCE_MANIFEST.json", "{}\n")
    _write_file(root / "runtime_native" / "tradebot_main.py", "def main(): pass\n")
    return root.resolve()


def test_runtime_ownership_payload_is_read_only_native(tmp_path, monkeypatch):
    root = _make_native_repo(tmp_path / "algotradify")
    for name in (
        "ALGOTRADIFY_ENGINE_ROOT",
        "TRADEBOT_ROOT",
        "CORE_BOT_ROOT",
        "CORE_BOT_RUNTIME_ROOT",
        "ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME",
    ):
        monkeypatch.delenv(name, raising=False)

    payload = build_runtime_ownership_payload(base_repo_root=root)

    assert payload["contract"] == "runtime_ownership_status_v1"
    assert payload["runtime_ownership"] == "NATIVE"
    assert payload["native_source_present"] is True
    assert payload["native_main_promoted"] is True
    assert payload["external_runtime_allowed"] is False
    assert payload["external_runtime_deprecated"] is True
    assert "deprecated" in payload["external_runtime_deprecation_message"]
    assert payload["external_runtime_used"] is False
    assert payload["can_start_native_runtime"] is True
    assert payload["read_only"] is True
    assert payload["audit_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None
    assert payload["live_mode_touched"] is False


def test_runtime_ownership_payload_reports_explicit_external_opt_in_warning(tmp_path, monkeypatch):
    root = _make_native_repo(tmp_path / "algotradify")
    monkeypatch.setenv("ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME", "true")

    payload = build_runtime_ownership_payload(base_repo_root=root)

    assert payload["runtime_ownership"] == "NATIVE"
    assert payload["external_runtime_allowed"] is True
    assert payload["external_runtime_deprecated"] is True
    assert payload["external_runtime_used"] is False
    assert any("external_runtime_fallback.deprecated" in warning for warning in payload["warnings"])
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False


def test_runtime_ownership_payload_reports_blockers_without_mutation(tmp_path, monkeypatch):
    root = tmp_path / "algotradify"
    root.mkdir()
    monkeypatch.setenv("ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME", "true")

    payload = build_runtime_ownership_payload(base_repo_root=root)

    assert payload["runtime_ownership"] == "WRAPPER_OR_EXTERNAL_COMPATIBLE"
    assert payload["can_start_native_runtime"] is False
    assert payload["blockers"]
    assert payload["external_runtime_deprecated"] is True
    assert payload["read_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["real_order_id"] is None


def test_runtime_ownership_route_installs_get_only_route(tmp_path):
    from fastapi import FastAPI

    root = _make_native_repo(tmp_path / "algotradify")
    app = FastAPI()

    install_runtime_ownership_route(app, repo_root_provider=lambda: root)

    matching = [route for route in app.routes if getattr(route, "path", None) == "/runtime/ownership"]
    assert len(matching) == 1
    methods = set(getattr(matching[0], "methods", set()))
    assert methods == {"GET"}


def test_runtime_ownership_route_does_not_expose_order_verbs(tmp_path):
    from fastapi import FastAPI

    root = _make_native_repo(tmp_path / "algotradify")
    app = FastAPI()
    install_runtime_ownership_route(app, repo_root_provider=lambda: root)

    route_text = "\n".join(str(getattr(route, "path", "")) for route in app.routes)
    forbidden = ["submit", "modify", "cancel", "exit", "order"]
    for marker in forbidden:
        assert marker not in route_text.lower()

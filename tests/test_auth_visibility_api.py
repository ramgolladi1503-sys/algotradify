from __future__ import annotations

from pathlib import Path

from api.auth_visibility import build_broker_auth_visibility_payload
from api.auth_visibility_route import install_auth_visibility_route


def test_auth_visibility_payload_is_local_only_and_sanitized(tmp_path, monkeypatch):
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    (runtime_root / "kite_access_token").write_text("tok_abcdefghijklmnopqrstuvwxyz\n", encoding="utf-8")
    monkeypatch.setenv("KITE_API_KEY", "api_key_123456")
    monkeypatch.setenv("KITE_API_SECRET", "secret_should_not_leak")
    monkeypatch.delenv("KITE_ACCESS_TOKEN", raising=False)

    payload = build_broker_auth_visibility_payload(runtime_artifact_root=runtime_root)

    assert payload["contract"] == "broker_auth_visibility_v1"
    assert payload["source"] == "local_files_env_only"
    assert payload["status"] in {"OK", "WARN"}
    assert payload["api_key_present"] is True
    assert payload["api_key_tail4"] == "3456"
    assert payload["api_secret_present"] is True
    assert payload["token_file_present"] is True
    assert payload["token_file_usable_shape"] is True
    assert payload["token_file_tail4"] == "wxyz"
    assert payload["can_validate_locally"] is True
    assert payload["read_only"] is True
    assert payload["auth_visibility_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert payload["profile_probe_called"] is False
    assert payload["token_mutated"] is False
    assert payload["raw_token_exposed"] is False
    assert payload["api_secret_exposed"] is False
    assert payload["real_order_id"] is None
    assert payload["live_mode_touched"] is False
    assert "secret_should_not_leak" not in str(payload)
    assert "tok_abcdefghijklmnopqrstuvwxyz" not in str(payload)


def test_auth_visibility_payload_blocks_missing_local_credentials(tmp_path, monkeypatch):
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    monkeypatch.delenv("KITE_API_SECRET", raising=False)
    monkeypatch.delenv("KITE_ACCESS_TOKEN", raising=False)

    payload = build_broker_auth_visibility_payload(runtime_artifact_root=runtime_root)

    assert payload["status"] == "BLOCKED"
    assert payload["auth_state"] == "BLOCKED_LOCAL"
    assert payload["can_validate_locally"] is False
    assert payload["login_required"] is True
    assert "KITE_API_KEY missing" in payload["blockers"]
    assert "usable Kite access token missing" in payload["blockers"]
    assert payload["broker_api_called"] is False
    assert payload["profile_probe_called"] is False
    assert payload["token_mutated"] is False


def test_auth_visibility_payload_uses_env_token_shape_without_raw_exposure(tmp_path, monkeypatch):
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    monkeypatch.setenv("KITE_API_KEY", "api_key_abcdef")
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "env_token_abcdefghijklmnopqrstuvwxyz")
    monkeypatch.delenv("KITE_API_SECRET", raising=False)

    payload = build_broker_auth_visibility_payload(runtime_artifact_root=runtime_root)

    assert payload["env_token_present"] is True
    assert payload["env_token_usable_shape"] is True
    assert payload["env_token_tail4"] == "wxyz"
    assert payload["can_validate_locally"] is True
    assert payload["can_attempt_login_locally"] is False
    assert payload["raw_token_exposed"] is False
    assert "env_token_abcdefghijklmnopqrstuvwxyz" not in str(payload)


def test_auth_visibility_route_installs_get_only_route(tmp_path):
    from fastapi import FastAPI

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    app = FastAPI()
    install_auth_visibility_route(app, runtime_artifact_root_provider=lambda: runtime_root)

    matching = [route for route in app.routes if getattr(route, "path", None) == "/broker/auth/visibility"]
    assert len(matching) == 1
    assert set(getattr(matching[0], "methods", set())) == {"GET"}


def test_auth_visibility_route_does_not_expose_mutation_verbs(tmp_path):
    from fastapi import FastAPI

    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    app = FastAPI()
    install_auth_visibility_route(app, runtime_artifact_root_provider=lambda: runtime_root)

    route_text = "\n".join(str(getattr(route, "path", "")) for route in app.routes)
    forbidden = ["login", "logout", "token", "refresh", "profile", "order", "start", "live"]
    for marker in forbidden:
        assert marker not in route_text.lower()

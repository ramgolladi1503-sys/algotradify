from __future__ import annotations

from dashboard.auth_visibility_panel import normalize_auth_visibility_panel, render_auth_visibility_panel


def _payload() -> dict:
    return {
        "status": "WARN",
        "auth_state": "NEEDS_ATTENTION",
        "source": "local_files_env_only",
        "api_key_present": True,
        "api_key_tail4": "3456",
        "api_secret_present": False,
        "token_file_present": True,
        "token_file_length": 32,
        "token_file_tail4": "wxyz",
        "token_file_usable_shape": True,
        "env_token_present": False,
        "env_token_length": 0,
        "env_token_tail4": "",
        "env_token_usable_shape": False,
        "can_validate_locally": True,
        "can_attempt_login_locally": False,
        "login_required": False,
        "operator_commands": {
            "login_only": "./run_live.sh --login-only",
            "validate_only": "./run_live.sh --validate-only",
            "sim_start": "python scripts/operator_boot.py sim",
            "paper_start": "python scripts/operator_boot.py paper",
        },
        "warnings": ["KITE_API_SECRET missing; login-only flow cannot run until set"],
        "blockers": [],
    }


def test_auth_visibility_panel_is_read_only_and_actionless():
    panel = normalize_auth_visibility_panel(_payload())

    assert panel["read_only_panel"] is True
    assert panel["allowed_actions"] == []
    assert "login_mutation" in panel["forbidden_actions"]
    assert "token_write" in panel["forbidden_actions"]
    assert "token_display" in panel["forbidden_actions"]
    assert "broker_profile_probe" in panel["forbidden_actions"]
    assert "submit_order" in panel["forbidden_actions"]
    assert "toggle_live" in panel["forbidden_actions"]
    assert panel["safe_flags"]["read_only"] is True
    assert panel["safe_flags"]["auth_visibility_only"] is True
    assert panel["safe_flags"]["is_order_action"] is False
    assert panel["safe_flags"]["broker_api_called"] is False
    assert panel["safe_flags"]["profile_probe_called"] is False
    assert panel["safe_flags"]["token_mutated"] is False
    assert panel["safe_flags"]["raw_token_exposed"] is False
    assert panel["safe_flags"]["api_secret_exposed"] is False
    assert panel["safe_flags"]["real_order_id"] is None
    assert panel["safe_flags"]["live_mode_touched"] is False


def test_auth_visibility_panel_does_not_expose_raw_token_or_secret_fields():
    payload = _payload()
    payload["raw_token"] = "should_not_render"
    payload["api_secret"] = "secret_should_not_render"

    panel = normalize_auth_visibility_panel(payload)

    assert "raw_token" not in panel
    assert "api_secret" not in panel
    assert "should_not_render" not in str(panel)
    assert "secret_should_not_render" not in str(panel)


def test_auth_visibility_panel_warning_badge():
    panel = normalize_auth_visibility_panel(_payload())

    assert panel["badge"] == "warning"
    assert panel["status"] == "WARN"
    assert panel["can_validate_locally"] is True
    assert panel["can_attempt_login_locally"] is False


def test_auth_visibility_panel_blocked_badge_when_blockers_exist():
    payload = _payload()
    payload["status"] = "BLOCKED"
    payload["blockers"] = ["usable Kite access token missing"]

    panel = normalize_auth_visibility_panel(payload)

    assert panel["badge"] == "blocked"
    assert panel["blockers"] == ["usable Kite access token missing"]


def test_auth_visibility_panel_renderer_uses_streamlit_write_only():
    calls: list[tuple[str, object]] = []

    class FakeStreamlit:
        def subheader(self, value):
            calls.append(("subheader", value))

        def caption(self, value):
            calls.append(("caption", value))

        def write(self, value):
            calls.append(("write", value))

    panel = render_auth_visibility_panel(FakeStreamlit(), _payload())

    assert panel["read_only_panel"] is True
    assert [name for name, _ in calls] == ["subheader", "caption", "write"]
    rendered = calls[-1][1]
    assert rendered["allowed_actions"] == []
    assert rendered["read_only_panel"] is True
    assert "operator_guidance" in rendered

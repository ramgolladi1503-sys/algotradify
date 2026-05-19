from __future__ import annotations

from dashboard.runtime_ownership_panel import normalize_runtime_ownership_panel, render_runtime_ownership_panel


def _native_payload() -> dict:
    return {
        "status": "WARN",
        "runtime_ownership": "NATIVE",
        "native_source_present": True,
        "native_main_promoted": True,
        "external_runtime_allowed": True,
        "external_runtime_used": False,
        "runtime_root": "/repo",
        "runtime_artifact_root": "/repo/.runtime",
        "can_start_native_runtime": True,
        "warnings": ["broker_token.available: optional in SIM"],
        "blockers": [],
    }


def test_runtime_ownership_panel_is_read_only_and_actionless():
    panel = normalize_runtime_ownership_panel(_native_payload())

    assert panel["read_only_panel"] is True
    assert panel["allowed_actions"] == []
    assert "submit_order" in panel["forbidden_actions"]
    assert "broker_call" in panel["forbidden_actions"]
    assert "toggle_live" in panel["forbidden_actions"]
    assert panel["safe_flags"]["read_only"] is True
    assert panel["safe_flags"]["audit_only"] is True
    assert panel["safe_flags"]["is_order_action"] is False
    assert panel["safe_flags"]["broker_api_called"] is False
    assert panel["safe_flags"]["real_order_id"] is None
    assert panel["safe_flags"]["live_mode_touched"] is False


def test_runtime_ownership_panel_native_warning_badge():
    panel = normalize_runtime_ownership_panel(_native_payload())

    assert panel["badge"] == "warning"
    assert panel["runtime_ownership"] == "NATIVE"
    assert panel["can_start_native_runtime"] is True
    assert panel["external_runtime_used"] is False


def test_runtime_ownership_panel_blocked_badge_when_blockers_exist():
    payload = _native_payload()
    payload["blockers"] = ["runtime_root.resolved: missing"]

    panel = normalize_runtime_ownership_panel(payload)

    assert panel["badge"] == "blocked"
    assert panel["blockers"] == ["runtime_root.resolved: missing"]


def test_runtime_ownership_panel_renderer_uses_streamlit_write_only():
    calls: list[tuple[str, object]] = []

    class FakeStreamlit:
        def subheader(self, value):
            calls.append(("subheader", value))

        def caption(self, value):
            calls.append(("caption", value))

        def write(self, value):
            calls.append(("write", value))

    panel = render_runtime_ownership_panel(FakeStreamlit(), _native_payload())

    assert panel["read_only_panel"] is True
    assert [name for name, _ in calls] == ["subheader", "caption", "write"]
    rendered = calls[-1][1]
    assert rendered["allowed_actions"] == []
    assert rendered["read_only_panel"] is True

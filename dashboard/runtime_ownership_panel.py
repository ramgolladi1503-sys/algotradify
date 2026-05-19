from __future__ import annotations

from typing import Any


SAFE_TRUE_FLAGS = {
    "read_only": True,
    "audit_only": True,
    "is_order_action": False,
    "broker_api_called": False,
    "real_order_id": None,
    "live_mode_touched": False,
}


def normalize_runtime_ownership_panel(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize runtime ownership API payload for Control Tower display.

    The normalized model is intentionally display-only. It contains no actions,
    no controls, no broker affordances, and no mutation payloads.
    """
    data = dict(payload or {})
    ownership = str(data.get("runtime_ownership") or "UNKNOWN")
    status = str(data.get("status") or "UNKNOWN")
    blockers = [str(item) for item in list(data.get("blockers") or [])]
    warnings = [str(item) for item in list(data.get("warnings") or [])]
    native_ready = bool(data.get("can_start_native_runtime"))
    external_used = bool(data.get("external_runtime_used"))

    badge = "native" if ownership == "NATIVE" and native_ready and not external_used else "attention"
    if blockers:
        badge = "blocked"
    elif warnings and badge == "native":
        badge = "warning"

    return {
        "title": "Runtime Ownership",
        "badge": badge,
        "status": status,
        "runtime_ownership": ownership,
        "native_source_present": bool(data.get("native_source_present")),
        "native_main_promoted": bool(data.get("native_main_promoted")),
        "external_runtime_used": external_used,
        "external_runtime_allowed": bool(data.get("external_runtime_allowed")),
        "runtime_root": data.get("runtime_root"),
        "runtime_artifact_root": data.get("runtime_artifact_root"),
        "can_start_native_runtime": native_ready,
        "warnings": warnings,
        "blockers": blockers,
        "safe_flags": dict(SAFE_TRUE_FLAGS),
        "read_only_panel": True,
        "allowed_actions": [],
        "forbidden_actions": [
            "submit_order",
            "modify_order",
            "cancel_order",
            "exit_position",
            "broker_call",
            "toggle_live",
            "write_runtime_state",
        ],
    }


def render_runtime_ownership_panel(st_module: Any, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Render read-only runtime ownership status in Streamlit.

    Returns the normalized panel model so tests can validate the exact display
    contract without importing Streamlit.
    """
    panel = normalize_runtime_ownership_panel(payload)
    st_module.subheader(panel["title"])
    st_module.caption(
        "Read-only runtime ownership status. No broker calls, order controls, or live toggles are available here."
    )
    st_module.write(
        {
            "badge": panel["badge"],
            "status": panel["status"],
            "runtime_ownership": panel["runtime_ownership"],
            "native_source_present": panel["native_source_present"],
            "native_main_promoted": panel["native_main_promoted"],
            "external_runtime_used": panel["external_runtime_used"],
            "runtime_root": panel["runtime_root"],
            "runtime_artifact_root": panel["runtime_artifact_root"],
            "warnings": panel["warnings"],
            "blockers": panel["blockers"],
            "read_only_panel": panel["read_only_panel"],
            "allowed_actions": panel["allowed_actions"],
        }
    )
    return panel

from __future__ import annotations

from typing import Any

SAFE_FLAGS = {
    "read_only": True,
    "auth_visibility_only": True,
    "is_order_action": False,
    "broker_api_called": False,
    "profile_probe_called": False,
    "token_mutated": False,
    "raw_token_exposed": False,
    "api_secret_exposed": False,
    "real_order_id": None,
    "live_mode_touched": False,
}


def normalize_auth_visibility_panel(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize broker auth visibility for Control Tower display only.

    This helper intentionally exposes no buttons, no token values, no login
    mutation payloads, and no broker action affordances.
    """
    data = dict(payload or {})
    status = str(data.get("status") or "UNKNOWN")
    blockers = [str(item) for item in list(data.get("blockers") or [])]
    warnings = [str(item) for item in list(data.get("warnings") or [])]

    badge = "ok" if status == "OK" else ("warning" if status == "WARN" else "blocked")
    commands = dict(data.get("operator_commands") or {})

    return {
        "title": "Broker Auth Visibility",
        "badge": badge,
        "status": status,
        "auth_state": str(data.get("auth_state") or "UNKNOWN"),
        "source": str(data.get("source") or "local_files_env_only"),
        "api_key_present": bool(data.get("api_key_present")),
        "api_key_tail4": str(data.get("api_key_tail4") or ""),
        "api_secret_present": bool(data.get("api_secret_present")),
        "token_file_present": bool(data.get("token_file_present")),
        "token_file_length": int(data.get("token_file_length") or 0),
        "token_file_tail4": str(data.get("token_file_tail4") or ""),
        "token_file_usable_shape": bool(data.get("token_file_usable_shape")),
        "env_token_present": bool(data.get("env_token_present")),
        "env_token_length": int(data.get("env_token_length") or 0),
        "env_token_tail4": str(data.get("env_token_tail4") or ""),
        "env_token_usable_shape": bool(data.get("env_token_usable_shape")),
        "can_validate_locally": bool(data.get("can_validate_locally")),
        "can_attempt_login_locally": bool(data.get("can_attempt_login_locally")),
        "login_required": bool(data.get("login_required")),
        "operator_guidance": {
            "login_only": commands.get("login_only", "./run_live.sh --login-only"),
            "validate_only": commands.get("validate_only", "./run_live.sh --validate-only"),
            "sim_start": commands.get("sim_start", "python scripts/operator_boot.py sim"),
            "paper_start": commands.get("paper_start", "python scripts/operator_boot.py paper"),
        },
        "warnings": warnings,
        "blockers": blockers,
        "safe_flags": dict(SAFE_FLAGS),
        "read_only_panel": True,
        "allowed_actions": [],
        "forbidden_actions": [
            "login_mutation",
            "token_write",
            "token_display",
            "broker_profile_probe",
            "submit_order",
            "modify_order",
            "cancel_order",
            "toggle_live",
        ],
    }


def render_auth_visibility_panel(st_module: Any, payload: dict[str, Any] | None) -> dict[str, Any]:
    panel = normalize_auth_visibility_panel(payload)
    st_module.subheader(panel["title"])
    st_module.caption(
        "Read-only local auth visibility. No raw tokens, login mutation, broker profile probe, or order controls are available here."
    )
    st_module.write(
        {
            "badge": panel["badge"],
            "status": panel["status"],
            "auth_state": panel["auth_state"],
            "source": panel["source"],
            "api_key_present": panel["api_key_present"],
            "api_key_tail4": panel["api_key_tail4"],
            "api_secret_present": panel["api_secret_present"],
            "token_file_present": panel["token_file_present"],
            "token_file_length": panel["token_file_length"],
            "token_file_tail4": panel["token_file_tail4"],
            "token_file_usable_shape": panel["token_file_usable_shape"],
            "env_token_present": panel["env_token_present"],
            "env_token_length": panel["env_token_length"],
            "env_token_tail4": panel["env_token_tail4"],
            "env_token_usable_shape": panel["env_token_usable_shape"],
            "can_validate_locally": panel["can_validate_locally"],
            "can_attempt_login_locally": panel["can_attempt_login_locally"],
            "login_required": panel["login_required"],
            "operator_guidance": panel["operator_guidance"],
            "warnings": panel["warnings"],
            "blockers": panel["blockers"],
            "read_only_panel": panel["read_only_panel"],
            "allowed_actions": panel["allowed_actions"],
        }
    )
    return panel

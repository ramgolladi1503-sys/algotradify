from __future__ import annotations

import os
from pathlib import Path
from typing import Any

CONTRACT = "broker_auth_visibility_v1"
MIN_TOKEN_LEN = 20


def _tail4(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[-4:] if len(text) >= 4 else text


def _read_token_file(path: Path) -> tuple[bool, str, str | None]:
    if not path.exists():
        return False, "", None
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return True, "", f"token_file_unreadable:{type(exc).__name__}"
    return True, raw, None


def _token_summary(raw: str) -> dict[str, Any]:
    token = str(raw or "").strip()
    return {
        "present": bool(token),
        "length": len(token),
        "tail4": _tail4(token),
        "has_whitespace": any(ch.isspace() for ch in str(raw or "")),
        "usable_shape": bool(token and len(token) >= MIN_TOKEN_LEN),
    }


def build_broker_auth_visibility_payload(*, runtime_artifact_root: Path | str | None = None) -> dict[str, Any]:
    """Build sanitized, local-only broker auth visibility payload.

    This must never call Kite/broker APIs, never run login, never mutate tokens,
    never expose raw credentials, and never touch live mode.
    """
    root = Path(runtime_artifact_root or Path.cwd() / ".runtime").expanduser().resolve()
    token_path = root / "kite_access_token"
    token_file_exists, token_raw, token_read_error = _read_token_file(token_path)
    token = _token_summary(token_raw)

    env_token = _token_summary(os.getenv("KITE_ACCESS_TOKEN", ""))
    api_key = str(os.getenv("KITE_API_KEY", "") or "").strip()
    api_secret = str(os.getenv("KITE_API_SECRET", "") or "").strip()

    token_usable = bool(token["usable_shape"] or env_token["usable_shape"])
    api_key_present = bool(api_key)
    api_secret_present = bool(api_secret)

    blockers: list[str] = []
    warnings: list[str] = []
    if not api_key_present:
        blockers.append("KITE_API_KEY missing")
    if not token_usable:
        blockers.append("usable Kite access token missing")
    if token_read_error:
        blockers.append(token_read_error)
    if token_file_exists and token["present"] and not token["usable_shape"]:
        blockers.append("kite_access_token file present but token shape is too short")
    if env_token["present"] and not env_token["usable_shape"]:
        blockers.append("KITE_ACCESS_TOKEN env var present but token shape is too short")
    if token["has_whitespace"]:
        warnings.append("kite_access_token file contains whitespace; startup strips it")
    if env_token["has_whitespace"]:
        warnings.append("KITE_ACCESS_TOKEN env var contains whitespace; startup strips it")
    if not api_secret_present:
        warnings.append("KITE_API_SECRET missing; login-only flow cannot run until set")

    status = "BLOCKED" if blockers else ("WARN" if warnings else "OK")
    auth_state = "READY_LOCAL" if status == "OK" else ("NEEDS_ATTENTION" if status == "WARN" else "BLOCKED_LOCAL")

    return {
        "contract": CONTRACT,
        "status": status,
        "auth_state": auth_state,
        "source": "local_files_env_only",
        "runtime_artifact_root": str(root),
        "token_file_path": str(token_path),
        "api_key_present": api_key_present,
        "api_key_tail4": _tail4(api_key),
        "api_secret_present": api_secret_present,
        "token_file_present": token_file_exists,
        "token_file_length": token["length"],
        "token_file_tail4": token["tail4"],
        "token_file_usable_shape": token["usable_shape"],
        "env_token_present": env_token["present"],
        "env_token_length": env_token["length"],
        "env_token_tail4": env_token["tail4"],
        "env_token_usable_shape": env_token["usable_shape"],
        "can_validate_locally": bool(api_key_present and token_usable),
        "can_attempt_login_locally": bool(api_key_present and api_secret_present),
        "login_required": not token_usable,
        "operator_commands": {
            "login_only": "./run_live.sh --login-only",
            "validate_only": "./run_live.sh --validate-only",
            "live_start": "./run_live.sh --start --i-understand-live-risk",
            "sim_start": "python scripts/operator_boot.py sim",
            "paper_start": "python scripts/operator_boot.py paper",
            "api_only": "python scripts/operator_boot.py ui-api --host 127.0.0.1 --port 8000",
        },
        "blockers": blockers,
        "warnings": warnings,
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

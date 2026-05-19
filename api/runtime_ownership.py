from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime_contract import run_preflight

CONTRACT = "runtime_ownership_status_v1"


def _collect_reasons(preflight: dict[str, Any], status: str) -> list[str]:
    reasons: list[str] = []
    for check in list(preflight.get("checks") or []):
        if not isinstance(check, dict):
            continue
        if str(check.get("status") or "").upper() != status:
            continue
        name = str(check.get("name") or "").strip()
        message = str(check.get("message") or "").strip()
        if name and message:
            reasons.append(f"{name}: {message}")
        elif name:
            reasons.append(name)
        elif message:
            reasons.append(message)
    return reasons


def build_runtime_ownership_payload(*, base_repo_root: Path | None = None) -> dict[str, Any]:
    """Build a read-only runtime ownership status payload.

    This function must not call broker APIs, start runtime workers, mutate runtime
    mode, or create orders. It only summarizes runtime_contract preflight output.
    """
    preflight = run_preflight(base_repo_root=base_repo_root, create_runtime_dirs=False)
    ownership = str(preflight.get("runtime_ownership") or "UNKNOWN")
    external_runtime_used = bool(preflight.get("external_runtime_used"))
    native_source_present = bool(preflight.get("native_source_present"))
    native_main_promoted = bool(preflight.get("native_main_promoted"))
    runtime_root = preflight.get("runtime_root")
    runtime_artifact_root = preflight.get("runtime_artifact_root")

    return {
        "contract": CONTRACT,
        "status": preflight.get("status"),
        "runtime_ownership": ownership,
        "native_source_present": native_source_present,
        "native_main_promoted": native_main_promoted,
        "native_required": bool(preflight.get("native_required")),
        "external_runtime_allowed": bool(preflight.get("external_runtime_allowed")),
        "external_runtime_used": external_runtime_used,
        "runtime_root": str(runtime_root) if runtime_root else None,
        "runtime_artifact_root": str(runtime_artifact_root) if runtime_artifact_root else None,
        "can_start_native_runtime": bool(ownership == "NATIVE" and native_source_present and native_main_promoted and not external_runtime_used),
        "warnings": _collect_reasons(preflight, "WARN"),
        "blockers": _collect_reasons(preflight, "FAIL"),
        "summary": dict(preflight.get("summary") or {}),
        "checked_at_source": "api.runtime_ownership.build_runtime_ownership_payload",
        "preflight_checked_at_source": preflight.get("checked_at_source"),
        "read_only": True,
        "audit_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "live_mode_touched": False,
    }

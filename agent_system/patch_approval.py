from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from typing import Any


AGENT_PATCH_APPROVAL_SCHEMA_VERSION = 1
AGENT_PATCH_APPROVAL_CONTRACT = "agent_patch_approval_v1"


class AgentPatchApprovalError(RuntimeError):
    """Raised when a patch-only approval decision cannot be safely recorded."""


def _safe_flags() -> dict[str, Any]:
    return {
        "read_only": True,
        "patch_approval_only": True,
        "allowed_for_patch": False,
        "allowed_for_runtime_wiring": False,
        "allowed_for_broker_api": False,
        "allowed_for_live_execution": False,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "real_order_id": None,
    }


def agent_patch_approval_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_PATCH_APPROVAL_SCHEMA_VERSION,
        "contract": AGENT_PATCH_APPROVAL_CONTRACT,
        "routes": [
            "POST /agent/tasks/{work_id}/approval",
            "POST /agent/tasks/{work_id}/rejection",
        ],
        "methods": ["POST"],
        "safe_defaults": _safe_flags(),
        "scope": "patch_approval_record_only_no_execution_no_broker_no_live_no_paper_orders",
    }


def _utc_iso(created_at: datetime | None = None) -> str:
    value = created_at or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _approval_dir(root_dir: str | Path) -> Path:
    return Path(root_dir) / "approvals"


def _approval_path(root_dir: str | Path, work_id: str) -> Path:
    return _approval_dir(root_dir) / f"{work_id}.json"


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, sort_keys=True, indent=2, default=str)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
        tmp.write(encoded)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _assert_safe_record(payload: Mapping[str, Any]) -> None:
    expected = _safe_flags()
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            raise AgentPatchApprovalError(f"UNSAFE_APPROVAL_{key.upper()}")
    if payload.get("allowed_for_patch") is True and payload.get("decision") != "APPROVED_FOR_PATCH":
        raise AgentPatchApprovalError("PATCH_PERMISSION_WITHOUT_APPROVAL")


def _clean_actor(value: str | None, field: str) -> str:
    if not isinstance(value, str):
        raise AgentPatchApprovalError(f"{field.upper()}_MUST_BE_STRING")
    cleaned = value.strip()
    if not cleaned:
        raise AgentPatchApprovalError(f"{field.upper()}_REQUIRED")
    return cleaned


def _clean_reason(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AgentPatchApprovalError("REASON_MUST_BE_STRING")
    cleaned = value.strip()
    return cleaned or None


def build_agent_patch_approval_record(
    *,
    work_id: str,
    task: Mapping[str, Any],
    approval_decision: Mapping[str, Any],
    approved_by: str | None,
    reason: str | None = None,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    actor = _clean_actor(approved_by, "approved_by")
    cleaned_reason = _clean_reason(reason)
    if task.get("work_id") != work_id:
        raise AgentPatchApprovalError("TASK_WORK_ID_MISMATCH")
    if approval_decision.get("approved") is not True:
        raise AgentPatchApprovalError("APPROVAL_DECISION_NOT_APPROVED")
    if approval_decision.get("allowed_for_patch") is not True:
        raise AgentPatchApprovalError("PATCH_NOT_ALLOWED")
    for key in ["allowed_for_runtime_wiring", "allowed_for_broker_api", "allowed_for_live_execution", "is_order_action", "broker_api_called", "live_mode_touched"]:
        if approval_decision.get(key) is True:
            raise AgentPatchApprovalError(f"UNSAFE_APPROVAL_DECISION_{key.upper()}")

    payload = {
        "schema_version": AGENT_PATCH_APPROVAL_SCHEMA_VERSION,
        "contract": AGENT_PATCH_APPROVAL_CONTRACT,
        "work_id": work_id,
        "decision": "APPROVED_FOR_PATCH",
        "approved": True,
        "approved_by": actor,
        "rejected_by": None,
        "reason": cleaned_reason,
        "created_at": _utc_iso(created_at),
        "source_agent": task.get("source_agent"),
        "action": task.get("action"),
        "risk_level": task.get("risk_level"),
        "task_state": task.get("state"),
        "approval_decision": dict(approval_decision),
        "metadata": {
            "scope": "patch_approval_record_only_no_execution",
        },
        **_safe_flags(),
    }
    payload["allowed_for_patch"] = True
    _assert_safe_record({**payload, "allowed_for_patch": False} if False else payload)
    return payload


def build_agent_patch_rejection_record(
    *,
    work_id: str,
    task: Mapping[str, Any],
    rejected_by: str | None,
    reason: str | None = None,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    actor = _clean_actor(rejected_by, "rejected_by")
    cleaned_reason = _clean_reason(reason)
    if task.get("work_id") != work_id:
        raise AgentPatchApprovalError("TASK_WORK_ID_MISMATCH")

    payload = {
        "schema_version": AGENT_PATCH_APPROVAL_SCHEMA_VERSION,
        "contract": AGENT_PATCH_APPROVAL_CONTRACT,
        "work_id": work_id,
        "decision": "REJECTED_FOR_PATCH",
        "approved": False,
        "approved_by": None,
        "rejected_by": actor,
        "reason": cleaned_reason,
        "created_at": _utc_iso(created_at),
        "source_agent": task.get("source_agent"),
        "action": task.get("action"),
        "risk_level": task.get("risk_level"),
        "task_state": task.get("state"),
        "approval_decision": None,
        "metadata": {
            "scope": "patch_rejection_record_only_no_execution",
        },
        **_safe_flags(),
    }
    _assert_safe_record(payload)
    return payload


def persist_agent_patch_approval(record: Mapping[str, Any], root_dir: str | Path = "runtime/agent_work") -> dict[str, Any]:
    if record.get("schema_version") != AGENT_PATCH_APPROVAL_SCHEMA_VERSION:
        raise AgentPatchApprovalError("APPROVAL_SCHEMA_UNSUPPORTED")
    _assert_safe_record(record)
    path = _approval_path(root_dir, str(record.get("work_id")))
    if path.exists():
        raise AgentPatchApprovalError("APPROVAL_DECISION_ALREADY_RECORDED")
    _write_json_atomic(path, record)
    return {
        "status": "CREATED",
        "approval_path": str(path),
        "work_id": record.get("work_id"),
        **_safe_flags(),
    }


def load_agent_patch_approval(root_dir: str | Path, work_id: str) -> dict[str, Any] | None:
    path = _approval_path(root_dir, work_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AgentPatchApprovalError(f"APPROVAL_FILE_CORRUPT:{path.name}") from exc
    if not isinstance(payload, dict):
        raise AgentPatchApprovalError(f"APPROVAL_FILE_NOT_OBJECT:{path.name}")
    if payload.get("schema_version") != AGENT_PATCH_APPROVAL_SCHEMA_VERSION:
        raise AgentPatchApprovalError(f"APPROVAL_FILE_SCHEMA_UNSUPPORTED:{path.name}")
    _assert_safe_record(payload)
    return payload

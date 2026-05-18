from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping


class AgentEvidenceError(RuntimeError):
    """Raised when agent evidence cannot be safely written."""


def _json_safe(payload: Any) -> Any:
    if payload is None:
        return None
    if hasattr(payload, "to_dict") and callable(payload.to_dict):
        return payload.to_dict()
    if hasattr(payload, "__dataclass_fields__"):
        return asdict(payload)
    if isinstance(payload, Mapping):
        return {str(key): _json_safe(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_json_safe(item) for item in payload]
    return payload


def _assert_safe_payload(payload: Mapping[str, Any]) -> None:
    safety = payload.get("safety")
    if not isinstance(safety, Mapping):
        raise AgentEvidenceError("SAFETY_BLOCK_MISSING")

    expected = {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
    }
    for key, expected_value in expected.items():
        if safety.get(key) != expected_value:
            raise AgentEvidenceError(f"UNSAFE_EVIDENCE_{key.upper()}")


def build_agent_evidence_payload(
    *,
    request: Any,
    scope_decision: Any,
    approval_decision: Any | None = None,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    now = created_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    payload: dict[str, Any] = {
        "schema_version": 1,
        "created_at": now.astimezone(timezone.utc).isoformat(),
        "request": _json_safe(request),
        "scope_decision": _json_safe(scope_decision),
        "approval_decision": _json_safe(approval_decision),
        "safety": {
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
        },
        "metadata": {
            "contract": "agent_evidence_v1",
            "scope": "local_audit_evidence_only_no_execution",
        },
    }
    _assert_safe_payload(payload)
    return payload


def write_agent_evidence(
    *,
    request: Any,
    scope_decision: Any,
    approval_decision: Any | None = None,
    root_dir: str | Path = "runtime/agent_work",
    created_at: datetime | None = None,
) -> dict[str, Any]:
    root = Path(root_dir)
    root.mkdir(parents=True, exist_ok=True)

    payload = build_agent_evidence_payload(
        request=request,
        scope_decision=scope_decision,
        approval_decision=approval_decision,
        created_at=created_at,
    )
    created = datetime.fromisoformat(payload["created_at"])
    date_key = created.strftime("%Y-%m-%d")

    latest_path = root / "agent_work_latest.json"
    daily_path = root / f"agent_work_{date_key}.jsonl"

    encoded_latest = json.dumps(payload, sort_keys=True, indent=2, default=str)
    encoded_line = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    with tempfile.NamedTemporaryFile("w", delete=False, dir=root, encoding="utf-8") as tmp:
        tmp.write(encoded_latest)
        tmp_path = Path(tmp.name)

    try:
        tmp_path.replace(latest_path)
        with daily_path.open("a", encoding="utf-8") as handle:
            handle.write(encoded_line + "\n")
    except Exception as exc:  # pragma: no cover - defensive wrapping for caller clarity.
        raise AgentEvidenceError("AGENT_EVIDENCE_WRITE_FAILED") from exc

    return {
        "latest_path": str(latest_path),
        "daily_path": str(daily_path),
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
        "metadata": {
            "contract": "agent_evidence_v1",
            "scope": "local_audit_evidence_only_no_execution",
        },
    }


def agent_evidence_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "contract": "agent_evidence_v1",
        "latest_file": "agent_work_latest.json",
        "daily_file_pattern": "agent_work_YYYY-MM-DD.jsonl",
        "safe_defaults": {
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
        },
        "scope": "local_audit_evidence_only_no_api_no_ui_no_execution",
    }

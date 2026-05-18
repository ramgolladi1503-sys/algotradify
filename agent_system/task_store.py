from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION, build_agent_work_id


TASK_STORE_SCHEMA_VERSION = 1


class AgentTaskStoreError(RuntimeError):
    """Raised when task storage cannot safely load or persist task records."""


@dataclass(frozen=True)
class AgentTaskRecord:
    schema_version: int
    work_id: str
    source_agent: str
    action: str
    state: str
    risk_level: str
    created_at: str
    request: dict[str, Any]
    scope_decision: dict[str, Any]
    approval_decision: dict[str, Any] | None
    evidence_ref: dict[str, Any] | None
    read_only: bool
    is_order_action: bool
    broker_api_called: bool
    live_mode_touched: bool
    allowed_for_live_execution: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _utc_iso(created_at: datetime | None) -> str:
    now = created_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).isoformat()


def _assert_safe_task_payload(payload: Mapping[str, Any]) -> None:
    expected = {
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            raise AgentTaskStoreError(f"UNSAFE_TASK_{key.upper()}")

    approval = payload.get("approval_decision")
    if isinstance(approval, Mapping):
        if approval.get("allowed_for_broker_api") is True:
            raise AgentTaskStoreError("UNSAFE_TASK_ALLOWED_FOR_BROKER_API")
        if approval.get("allowed_for_live_execution") is True:
            raise AgentTaskStoreError("UNSAFE_TASK_ALLOWED_FOR_LIVE_EXECUTION")
        if approval.get("allowed_for_runtime_wiring") is True:
            raise AgentTaskStoreError("UNSAFE_TASK_ALLOWED_FOR_RUNTIME_WIRING")


def build_agent_task_record(
    *,
    request: Any,
    scope_decision: Any,
    approval_decision: Any | None = None,
    evidence_ref: Mapping[str, Any] | None = None,
    created_at: datetime | None = None,
) -> AgentTaskRecord:
    request_payload = _json_safe(request)
    scope_payload = _json_safe(scope_decision)
    approval_payload = _json_safe(approval_decision)
    evidence_payload = _json_safe(evidence_ref)

    if not isinstance(request_payload, Mapping):
        raise AgentTaskStoreError("TASK_REQUEST_MUST_BE_OBJECT")
    if not isinstance(scope_payload, Mapping):
        raise AgentTaskStoreError("TASK_SCOPE_DECISION_MUST_BE_OBJECT")
    if approval_payload is not None and not isinstance(approval_payload, Mapping):
        raise AgentTaskStoreError("TASK_APPROVAL_DECISION_MUST_BE_OBJECT")

    work_id = scope_payload.get("work_id") or build_agent_work_id(request)
    state = str(scope_payload.get("state") or "UNKNOWN")
    risk_level = str(scope_payload.get("risk_level") or "UNKNOWN")

    record = AgentTaskRecord(
        schema_version=TASK_STORE_SCHEMA_VERSION,
        work_id=str(work_id),
        source_agent=str(request_payload.get("source_agent", "")),
        action=str(request_payload.get("action", "")),
        state=state,
        risk_level=risk_level,
        created_at=_utc_iso(created_at),
        request=dict(request_payload),
        scope_decision=dict(scope_payload),
        approval_decision=dict(approval_payload) if isinstance(approval_payload, Mapping) else None,
        evidence_ref=dict(evidence_payload) if isinstance(evidence_payload, Mapping) else None,
        read_only=True,
        is_order_action=False,
        broker_api_called=False,
        live_mode_touched=False,
        allowed_for_live_execution=False,
        metadata={
            "contract": "agent_task_store_v1",
            "scope": "local_task_record_only_no_api_no_ui_no_execution",
        },
    )
    _assert_safe_task_payload(record.to_dict())
    return record


def _root(root_dir: str | Path) -> Path:
    return Path(root_dir)


def _tasks_dir(root_dir: str | Path) -> Path:
    return _root(root_dir) / "tasks"


def _index_path(root_dir: str | Path) -> Path:
    return _root(root_dir) / "agent_task_index.json"


def _task_path(root_dir: str | Path, work_id: str) -> Path:
    return _tasks_dir(root_dir) / f"{work_id}.json"


def _stable_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _dedupe_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "work_id": payload.get("work_id"),
        "source_agent": payload.get("source_agent"),
        "action": payload.get("action"),
        "state": payload.get("state"),
        "risk_level": payload.get("risk_level"),
        "request": payload.get("request"),
        "scope_decision": payload.get("scope_decision"),
        "approval_decision": payload.get("approval_decision"),
        "evidence_ref": payload.get("evidence_ref"),
        "read_only": payload.get("read_only"),
        "is_order_action": payload.get("is_order_action"),
        "broker_api_called": payload.get("broker_api_called"),
        "live_mode_touched": payload.get("live_mode_touched"),
        "allowed_for_live_execution": payload.get("allowed_for_live_execution"),
    }


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, sort_keys=True, indent=2, default=str)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
        tmp.write(encoded)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _load_task_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AgentTaskStoreError(f"TASK_FILE_CORRUPT:{path.name}") from exc
    if not isinstance(payload, dict):
        raise AgentTaskStoreError(f"TASK_FILE_NOT_OBJECT:{path.name}")
    if payload.get("schema_version") != TASK_STORE_SCHEMA_VERSION:
        raise AgentTaskStoreError(f"TASK_FILE_SCHEMA_UNSUPPORTED:{path.name}")
    _assert_safe_task_payload(payload)
    return payload


def load_agent_task(root_dir: str | Path, work_id: str) -> dict[str, Any] | None:
    path = _task_path(root_dir, work_id)
    if not path.exists():
        return None
    return _load_task_file(path)


def rebuild_agent_task_index(root_dir: str | Path) -> dict[str, Any]:
    tasks_dir = _tasks_dir(root_dir)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for path in sorted(tasks_dir.glob("*.json")):
        payload = _load_task_file(path)
        records.append(
            {
                "work_id": payload["work_id"],
                "source_agent": payload["source_agent"],
                "action": payload["action"],
                "state": payload["state"],
                "risk_level": payload["risk_level"],
                "created_at": payload["created_at"],
                "read_only": True,
                "is_order_action": False,
                "broker_api_called": False,
                "live_mode_touched": False,
                "allowed_for_live_execution": False,
            }
        )

    index = {
        "schema_version": TASK_STORE_SCHEMA_VERSION,
        "contract": "agent_task_index_v1",
        "count": len(records),
        "records": records,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
        "metadata": {
            "scope": "local_task_index_only_no_api_no_ui_no_execution",
        },
    }
    _assert_safe_task_payload(index)
    _write_json_atomic(_index_path(root_dir), index)
    return index


def persist_agent_task(record: AgentTaskRecord, root_dir: str | Path = "runtime/agent_work") -> dict[str, Any]:
    payload = record.to_dict()
    _assert_safe_task_payload(payload)

    path = _task_path(root_dir, record.work_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    status = "CREATED"
    if path.exists():
        existing = _load_task_file(path)
        if _stable_json(_dedupe_payload(existing)) != _stable_json(_dedupe_payload(payload)):
            raise AgentTaskStoreError("TASK_ID_CONFLICT")
        status = "EXISTS"
    else:
        _write_json_atomic(path, payload)

    index = rebuild_agent_task_index(root_dir)
    return {
        "status": status,
        "task_path": str(path),
        "index_path": str(_index_path(root_dir)),
        "work_id": record.work_id,
        "index_count": index["count"],
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
    }


def query_agent_tasks(
    root_dir: str | Path = "runtime/agent_work",
    *,
    work_id: str | None = None,
    source_agent: str | None = None,
    action: str | None = None,
    state: str | None = None,
    risk_level: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    index = rebuild_agent_task_index(root_dir)
    records = index["records"]

    def matches(record: Mapping[str, Any]) -> bool:
        if work_id and record.get("work_id") != work_id:
            return False
        if source_agent and record.get("source_agent") != source_agent:
            return False
        if action and record.get("action") != action:
            return False
        if state and record.get("state") != state:
            return False
        if risk_level and record.get("risk_level") != risk_level:
            return False
        if created_from and record.get("created_at", "") < created_from:
            return False
        if created_to and record.get("created_at", "") > created_to:
            return False
        return True

    filtered = [record for record in records if matches(record)]
    if limit is not None:
        if limit < 0:
            raise AgentTaskStoreError("LIMIT_MUST_BE_NON_NEGATIVE")
        filtered = filtered[:limit]

    return {
        "schema_version": TASK_STORE_SCHEMA_VERSION,
        "contract": "agent_task_query_v1",
        "source_count": len(records),
        "result_count": len(filtered),
        "records": filtered,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "live_mode_touched": False,
        "allowed_for_live_execution": False,
    }


def agent_task_store_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": TASK_STORE_SCHEMA_VERSION,
        "contract": "agent_task_store_v1",
        "tasks_dir": "runtime/agent_work/tasks",
        "index_file": "runtime/agent_work/agent_task_index.json",
        "query_filters": [
            "work_id",
            "source_agent",
            "action",
            "state",
            "risk_level",
            "created_from",
            "created_to",
            "limit",
        ],
        "safe_defaults": {
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
        },
        "scope": "local_task_store_only_no_api_no_ui_no_execution",
    }

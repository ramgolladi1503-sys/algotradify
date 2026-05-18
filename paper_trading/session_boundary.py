from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from paper_trading.persistence import (
    PaperEvidencePersistenceStatus,
    load_paper_evidence_records,
    write_paper_evidence_record,
)


PAPER_SESSION_BOUNDARY_SCHEMA_VERSION = "1.0"
PAPER_SESSION_BOUNDARY_RECORD_TYPE = "PAPER_SESSION_BOUNDARY"


class PaperSessionBoundaryStatus(StrEnum):
    BUILT = "BUILT"
    MARKED = "MARKED"
    LOADED = "LOADED"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


class PaperSessionBoundaryType(StrEnum):
    SESSION_START = "SESSION_START"
    SESSION_END = "SESSION_END"
    RESET_MARKER = "RESET_MARKER"


@dataclass(frozen=True)
class PaperSessionBoundaryResult:
    status: PaperSessionBoundaryStatus
    session_id: str | None = None
    boundary_type: str | None = None
    record: dict[str, Any] | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    persistence: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_SESSION_BOUNDARY_SCHEMA_VERSION

    @property
    def paper_only(self) -> bool:
        return True

    @property
    def read_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    @property
    def broker_api_called(self) -> bool:
        return False

    @property
    def real_order_id(self) -> None:
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "boundary_result_type": "PAPER_SESSION_BOUNDARY_RESULT",
            "status": self.status.value,
            "session_id": self.session_id,
            "boundary_type": self.boundary_type,
            "record": deepcopy(self.record),
            "record_count": len(self.records),
            "records": deepcopy(self.records),
            "persistence": deepcopy(self.persistence),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_session_boundary_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_SESSION_BOUNDARY_SCHEMA_VERSION,
        "boundary_result_type": "PAPER_SESSION_BOUNDARY_RESULT",
        "record_type": PAPER_SESSION_BOUNDARY_RECORD_TYPE,
        "statuses": [status.value for status in PaperSessionBoundaryStatus],
        "allowed_boundary_types": [boundary_type.value for boundary_type in PaperSessionBoundaryType],
        "required_record_keys": [
            "schema_version",
            "record_type",
            "session_id",
            "boundary_type",
            "created_at_epoch",
            "reason",
            "metadata",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_result_keys": [
            "schema_version",
            "boundary_result_type",
            "status",
            "session_id",
            "boundary_type",
            "record",
            "record_count",
            "records",
            "persistence",
            "blockers",
            "warnings",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "safe_flags": {
            "paper_only": True,
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
        "scope_boundary": [
            "local_paper_session_boundary_only",
            "reset_marker_is_non_destructive",
            "no_delete",
            "no_truncate",
            "no_runtime_wiring",
            "no_api",
            "no_ui",
            "no_broker_execution",
            "no_live_orders",
            "no_strategy_work",
        ],
    }


def build_paper_session_id(*, trading_date: str | None, session_label: str | None, namespace: str = "paper") -> str:
    seed = "|".join([
        str(namespace or "paper").strip(),
        str(trading_date or "").strip(),
        str(session_label or "").strip(),
    ])
    return f"paper-session-{sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def build_paper_session_boundary_record(
    *,
    session_id: str | None,
    boundary_type: str | None,
    created_at_epoch: float | None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PaperSessionBoundaryResult:
    record = {
        "schema_version": PAPER_SESSION_BOUNDARY_SCHEMA_VERSION,
        "record_type": PAPER_SESSION_BOUNDARY_RECORD_TYPE,
        "session_id": _str_or_none(session_id),
        "boundary_type": _str_or_none(boundary_type),
        "created_at_epoch": _float_or_none(created_at_epoch),
        "reason": _str_or_none(reason),
        "metadata": deepcopy(metadata or {}),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    blockers = validate_paper_session_boundary_record(record)
    if blockers:
        return PaperSessionBoundaryResult(
            status=PaperSessionBoundaryStatus.BLOCKED,
            session_id=_str_or_none(session_id),
            boundary_type=_str_or_none(boundary_type),
            record=record,
            blockers=blockers,
        )
    return PaperSessionBoundaryResult(
        status=PaperSessionBoundaryStatus.BUILT,
        session_id=record["session_id"],
        boundary_type=record["boundary_type"],
        record=record,
    )


def mark_paper_session_boundary(
    path: str | Path | None,
    *,
    session_id: str | None,
    boundary_type: str | None,
    created_at_epoch: float | None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PaperSessionBoundaryResult:
    destructive_blockers = _destructive_reset_blockers(metadata or {})
    if destructive_blockers:
        return PaperSessionBoundaryResult(
            status=PaperSessionBoundaryStatus.BLOCKED,
            session_id=_str_or_none(session_id),
            boundary_type=_str_or_none(boundary_type),
            blockers=destructive_blockers,
        )
    built = build_paper_session_boundary_record(
        session_id=session_id,
        boundary_type=boundary_type,
        created_at_epoch=created_at_epoch,
        reason=reason,
        metadata=metadata,
    )
    if built.status == PaperSessionBoundaryStatus.BLOCKED or not built.record:
        return built

    write_result = write_paper_evidence_record(
        path,
        record_type=PAPER_SESSION_BOUNDARY_RECORD_TYPE,
        cycle_id=built.record["session_id"],
        payload=built.record,
        created_at_epoch=created_at_epoch,
        source="paper_session_boundary",
    )
    write_payload = write_result.to_dict()
    if write_result.status == PaperEvidencePersistenceStatus.BLOCKED:
        return PaperSessionBoundaryResult(
            status=PaperSessionBoundaryStatus.BLOCKED,
            session_id=built.session_id,
            boundary_type=built.boundary_type,
            record=built.record,
            persistence=write_payload,
            blockers=_prefixed("PERSISTENCE_WRITE", write_payload.get("blockers") or ["PAPER_SESSION_BOUNDARY_WRITE_BLOCKED"]),
            warnings=write_payload.get("warnings") or [],
        )

    return PaperSessionBoundaryResult(
        status=PaperSessionBoundaryStatus.MARKED,
        session_id=built.session_id,
        boundary_type=built.boundary_type,
        record=built.record,
        persistence=write_payload,
        warnings=write_payload.get("warnings") or [],
    )


def load_paper_session_boundaries(path: str | Path | None) -> PaperSessionBoundaryResult:
    read_result = load_paper_evidence_records(path)
    read_payload = read_result.to_dict()
    if read_result.status == PaperEvidencePersistenceStatus.BLOCKED:
        return PaperSessionBoundaryResult(
            status=PaperSessionBoundaryStatus.BLOCKED,
            persistence=read_payload,
            blockers=_prefixed("PERSISTENCE_LOAD", read_payload.get("blockers") or ["PAPER_SESSION_BOUNDARY_LOAD_BLOCKED"]),
            warnings=read_payload.get("warnings") or [],
        )
    if read_result.status == PaperEvidencePersistenceStatus.EMPTY:
        return PaperSessionBoundaryResult(
            status=PaperSessionBoundaryStatus.EMPTY,
            persistence=read_payload,
            warnings=read_payload.get("warnings") or [],
        )

    boundary_records: list[dict[str, Any]] = []
    blockers: list[str] = []
    for index, evidence_record in enumerate(read_payload.get("records") or []):
        if evidence_record.get("record_type") != PAPER_SESSION_BOUNDARY_RECORD_TYPE:
            continue
        payload = evidence_record.get("payload")
        if not isinstance(payload, dict):
            blockers.append(f"PAPER_SESSION_BOUNDARY_RECORD_{index}_PAYLOAD_MUST_BE_OBJECT")
            continue
        record_blockers = validate_paper_session_boundary_record(payload)
        if record_blockers:
            blockers.extend(f"RECORD_{index}_{blocker}" for blocker in record_blockers)
            continue
        boundary_records.append(payload)

    if blockers:
        return PaperSessionBoundaryResult(
            status=PaperSessionBoundaryStatus.BLOCKED,
            persistence=read_payload,
            blockers=_dedupe(blockers),
            warnings=read_payload.get("warnings") or [],
        )
    if not boundary_records:
        return PaperSessionBoundaryResult(
            status=PaperSessionBoundaryStatus.EMPTY,
            persistence=read_payload,
            warnings=_dedupe([*(read_payload.get("warnings") or []), "PAPER_SESSION_BOUNDARY_NO_BOUNDARY_RECORDS"]),
        )
    return PaperSessionBoundaryResult(
        status=PaperSessionBoundaryStatus.LOADED,
        records=boundary_records,
        persistence=read_payload,
        warnings=read_payload.get("warnings") or [],
    )


def validate_paper_session_boundary_record(record: dict[str, Any] | None) -> list[str]:
    if record is None:
        return ["PAPER_SESSION_BOUNDARY_RECORD_REQUIRED"]
    if not isinstance(record, dict):
        return ["PAPER_SESSION_BOUNDARY_RECORD_MUST_BE_OBJECT"]

    blockers: list[str] = []
    for key in paper_session_boundary_schema_contract()["required_record_keys"]:
        if key not in record:
            blockers.append(f"PAPER_SESSION_BOUNDARY_RECORD_MISSING_{key.upper()}")

    if record.get("record_type") != PAPER_SESSION_BOUNDARY_RECORD_TYPE:
        blockers.append("PAPER_SESSION_BOUNDARY_RECORD_TYPE_INVALID")
    if not _str_or_none(record.get("session_id")):
        blockers.append("PAPER_SESSION_BOUNDARY_SESSION_ID_REQUIRED")
    boundary_type = _str_or_none(record.get("boundary_type"))
    allowed = {value.value for value in PaperSessionBoundaryType}
    if boundary_type not in allowed:
        blockers.append("PAPER_SESSION_BOUNDARY_TYPE_INVALID")
    if record.get("created_at_epoch") is None:
        blockers.append("PAPER_SESSION_BOUNDARY_CREATED_AT_EPOCH_REQUIRED")
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        blockers.append("PAPER_SESSION_BOUNDARY_METADATA_MUST_BE_OBJECT")
    else:
        blockers.extend(_unsafe_payload_blockers("METADATA", metadata))
        blockers.extend(_destructive_reset_blockers(metadata))

    if record.get("paper_only") is not True:
        blockers.append("PAPER_SESSION_BOUNDARY_UNSAFE_PAPER_ONLY_FLAG")
    if record.get("read_only") is not True:
        blockers.append("PAPER_SESSION_BOUNDARY_UNSAFE_READ_ONLY_FLAG")
    if record.get("is_order_action") is not False:
        blockers.append("PAPER_SESSION_BOUNDARY_UNSAFE_ORDER_ACTION_FLAG")
    if record.get("broker_api_called") is not False:
        blockers.append("PAPER_SESSION_BOUNDARY_UNSAFE_BROKER_API_FLAG")
    if record.get("real_order_id") is not None:
        blockers.append("PAPER_SESSION_BOUNDARY_UNSAFE_REAL_ORDER_ID")
    return _dedupe(blockers)


def _unsafe_payload_blockers(name: str, payload: Any) -> list[str]:
    if payload is None:
        return []
    if not isinstance(payload, dict):
        return [f"PAPER_SESSION_BOUNDARY_{name}_MUST_BE_OBJECT"]
    blockers: list[str] = []
    for path, key, value in _walk_dict(payload):
        if key == "paper_only" and value is not True:
            blockers.append(f"PAPER_SESSION_BOUNDARY_{name}_{path}_UNSAFE_PAPER_ONLY_FLAG")
        if key == "read_only" and value is not True:
            blockers.append(f"PAPER_SESSION_BOUNDARY_{name}_{path}_UNSAFE_READ_ONLY_FLAG")
        if key == "is_order_action" and value is not False:
            blockers.append(f"PAPER_SESSION_BOUNDARY_{name}_{path}_UNSAFE_ORDER_ACTION_FLAG")
        if key == "broker_api_called" and value is True:
            blockers.append(f"PAPER_SESSION_BOUNDARY_{name}_{path}_BROKER_API_CALLED")
        if key == "real_order_id" and value not in (None, ""):
            blockers.append(f"PAPER_SESSION_BOUNDARY_{name}_{path}_REAL_ORDER_ID_PRESENT")
    return blockers


def _destructive_reset_blockers(metadata: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    destructive_keys = {"delete", "deleted", "truncate", "truncated", "rewrite", "rewritten", "destructive", "remove_history"}
    for path, key, value in _walk_dict(metadata):
        if key.lower() in destructive_keys and bool(value):
            blockers.append(f"PAPER_SESSION_BOUNDARY_{path}_DESTRUCTIVE_RESET_FORBIDDEN")
    return blockers


def _walk_dict(payload: dict[str, Any], prefix: str = "ROOT"):
    for key, value in payload.items():
        path = f"{prefix}_{str(key).upper()}"
        yield path, str(key), value
        if isinstance(value, dict):
            yield from _walk_dict(value, prefix=path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    yield from _walk_dict(item, prefix=f"{path}_{index}")


def _str_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prefixed(source: str, blockers: list[str]) -> list[str]:
    return [f"PAPER_SESSION_BOUNDARY_{source}_{blocker}" for blocker in blockers]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

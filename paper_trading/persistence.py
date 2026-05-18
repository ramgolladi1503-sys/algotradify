from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any


PAPER_EVIDENCE_PERSISTENCE_SCHEMA_VERSION = "1.0"


class PaperEvidencePersistenceStatus(StrEnum):
    WRITTEN = "WRITTEN"
    LOADED = "LOADED"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperEvidenceRecord:
    record_type: str
    cycle_id: str
    payload: dict[str, Any]
    candidate_id: str | None = None
    strategy_id: str | None = None
    created_at_epoch: float | None = None
    source: str = "paper_evidence_persistence"
    schema_version: str = PAPER_EVIDENCE_PERSISTENCE_SCHEMA_VERSION

    @property
    def payload_hash(self) -> str:
        return stable_paper_evidence_payload_hash(self.payload)

    @property
    def record_id(self) -> str:
        seed = "|".join(
            [
                self.schema_version,
                self.record_type,
                self.cycle_id,
                self.candidate_id or "",
                self.strategy_id or "",
                self.payload_hash,
            ]
        )
        return f"paper-evidence-{sha256(seed.encode('utf-8')).hexdigest()[:16]}"

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
            "record_type": self.record_type,
            "record_id": self.record_id,
            "cycle_id": self.cycle_id,
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "created_at_epoch": self.created_at_epoch,
            "source": self.source,
            "payload": deepcopy(self.payload),
            "payload_hash": self.payload_hash,
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


@dataclass(frozen=True)
class PaperEvidenceWriteResult:
    written: bool
    status: PaperEvidencePersistenceStatus
    path: str | None = None
    record: dict[str, Any] | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_EVIDENCE_PERSISTENCE_SCHEMA_VERSION

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
            "persistence_type": "PAPER_EVIDENCE_JSONL_PERSISTENCE",
            "operation": "WRITE",
            "written": self.written,
            "status": self.status.value,
            "path": self.path,
            "record": deepcopy(self.record),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


@dataclass(frozen=True)
class PaperEvidenceReadResult:
    loaded: bool
    status: PaperEvidencePersistenceStatus
    path: str | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_EVIDENCE_PERSISTENCE_SCHEMA_VERSION

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
            "persistence_type": "PAPER_EVIDENCE_JSONL_PERSISTENCE",
            "operation": "READ",
            "loaded": self.loaded,
            "status": self.status.value,
            "path": self.path,
            "record_count": len(self.records),
            "records": deepcopy(self.records),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_evidence_persistence_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_EVIDENCE_PERSISTENCE_SCHEMA_VERSION,
        "persistence_type": "PAPER_EVIDENCE_JSONL_PERSISTENCE",
        "format": "JSONL",
        "statuses": [status.value for status in PaperEvidencePersistenceStatus],
        "required_record_keys": [
            "schema_version",
            "record_type",
            "record_id",
            "cycle_id",
            "candidate_id",
            "strategy_id",
            "created_at_epoch",
            "source",
            "payload",
            "payload_hash",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_write_result_keys": [
            "schema_version",
            "persistence_type",
            "operation",
            "written",
            "status",
            "path",
            "record",
            "blockers",
            "warnings",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_read_result_keys": [
            "schema_version",
            "persistence_type",
            "operation",
            "loaded",
            "status",
            "path",
            "record_count",
            "records",
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
            "local_jsonl_only",
            "paper_evidence_only",
            "no_runtime_wiring",
            "no_api",
            "no_ui",
            "no_broker_execution",
            "no_live_orders",
            "no_strategy_work",
        ],
    }


def write_paper_evidence_record(
    path: str | Path | None,
    *,
    record_type: str | None,
    cycle_id: str | None,
    payload: dict[str, Any] | None,
    candidate_id: str | None = None,
    strategy_id: str | None = None,
    created_at_epoch: float | None = None,
    source: str = "paper_evidence_persistence",
) -> PaperEvidenceWriteResult:
    path_text = _normalize_path(path)
    blockers = validate_paper_evidence_write_inputs(
        path=path,
        record_type=record_type,
        cycle_id=cycle_id,
        payload=payload,
    )
    if blockers:
        return PaperEvidenceWriteResult(
            written=False,
            status=PaperEvidencePersistenceStatus.BLOCKED,
            path=path_text,
            blockers=blockers,
        )

    record = PaperEvidenceRecord(
        record_type=str(record_type).strip(),
        cycle_id=str(cycle_id).strip(),
        payload=deepcopy(payload or {}),
        candidate_id=_str_or_none(candidate_id),
        strategy_id=_str_or_none(strategy_id),
        created_at_epoch=_float_or_none(created_at_epoch),
        source=_str_or_none(source) or "paper_evidence_persistence",
    ).to_dict()
    record_blockers = validate_paper_evidence_record(record)
    if record_blockers:
        return PaperEvidenceWriteResult(
            written=False,
            status=PaperEvidencePersistenceStatus.BLOCKED,
            path=path_text,
            record=record,
            blockers=record_blockers,
        )

    target = Path(path_text or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(_canonical_json(record) + "\n")

    return PaperEvidenceWriteResult(
        written=True,
        status=PaperEvidencePersistenceStatus.WRITTEN,
        path=str(target),
        record=record,
    )


def load_paper_evidence_records(path: str | Path | None) -> PaperEvidenceReadResult:
    path_text = _normalize_path(path)
    blockers = validate_paper_evidence_path(path)
    if blockers:
        return PaperEvidenceReadResult(
            loaded=False,
            status=PaperEvidencePersistenceStatus.BLOCKED,
            path=path_text,
            blockers=blockers,
        )

    source = Path(path_text or "")
    if not source.exists():
        return PaperEvidenceReadResult(
            loaded=True,
            status=PaperEvidencePersistenceStatus.EMPTY,
            path=str(source),
            warnings=["PAPER_EVIDENCE_FILE_MISSING_EMPTY"],
        )
    if source.stat().st_size == 0:
        return PaperEvidenceReadResult(
            loaded=True,
            status=PaperEvidencePersistenceStatus.EMPTY,
            path=str(source),
            warnings=["PAPER_EVIDENCE_FILE_EMPTY"],
        )

    records: list[dict[str, Any]] = []
    blockers: list[str] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                blockers.append(f"PAPER_EVIDENCE_CORRUPT_JSONL_LINE_{line_no}")
                continue
            if not isinstance(parsed, dict):
                blockers.append(f"PAPER_EVIDENCE_NON_OBJECT_JSONL_LINE_{line_no}")
                continue
            record_blockers = validate_paper_evidence_record(parsed)
            if record_blockers:
                blockers.extend(f"LINE_{line_no}_{blocker}" for blocker in record_blockers)
                continue
            records.append(parsed)

    if blockers:
        return PaperEvidenceReadResult(
            loaded=False,
            status=PaperEvidencePersistenceStatus.BLOCKED,
            path=str(source),
            records=[],
            blockers=_dedupe(blockers),
        )
    if not records:
        return PaperEvidenceReadResult(
            loaded=True,
            status=PaperEvidencePersistenceStatus.EMPTY,
            path=str(source),
            warnings=["PAPER_EVIDENCE_NO_RECORDS_LOADED"],
        )
    return PaperEvidenceReadResult(
        loaded=True,
        status=PaperEvidencePersistenceStatus.LOADED,
        path=str(source),
        records=records,
    )


def validate_paper_evidence_write_inputs(
    *,
    path: str | Path | None,
    record_type: str | None,
    cycle_id: str | None,
    payload: dict[str, Any] | None,
) -> list[str]:
    blockers = validate_paper_evidence_path(path)
    if not _str_or_none(record_type):
        blockers.append("PAPER_EVIDENCE_RECORD_TYPE_REQUIRED")
    if not _str_or_none(cycle_id):
        blockers.append("PAPER_EVIDENCE_CYCLE_ID_REQUIRED")
    if payload is None:
        blockers.append("PAPER_EVIDENCE_PAYLOAD_REQUIRED")
    elif not isinstance(payload, dict):
        blockers.append("PAPER_EVIDENCE_PAYLOAD_MUST_BE_OBJECT")
    else:
        blockers.extend(_unsafe_payload_blockers("PAYLOAD", payload))
    return _dedupe(blockers)


def validate_paper_evidence_path(path: str | Path | None) -> list[str]:
    if path is None:
        return ["PAPER_EVIDENCE_PATH_REQUIRED"]
    if not isinstance(path, (str, Path)):
        return ["PAPER_EVIDENCE_PATH_MUST_BE_STRING_OR_PATH"]
    if not _normalize_path(path):
        return ["PAPER_EVIDENCE_PATH_REQUIRED"]
    return []


def validate_paper_evidence_record(record: dict[str, Any] | None) -> list[str]:
    if record is None:
        return ["PAPER_EVIDENCE_RECORD_REQUIRED"]
    if not isinstance(record, dict):
        return ["PAPER_EVIDENCE_RECORD_MUST_BE_OBJECT"]
    blockers: list[str] = []
    for key in paper_evidence_persistence_schema_contract()["required_record_keys"]:
        if key not in record:
            blockers.append(f"PAPER_EVIDENCE_RECORD_MISSING_{key.upper()}")
    if not _str_or_none(record.get("record_type")):
        blockers.append("PAPER_EVIDENCE_RECORD_TYPE_REQUIRED")
    if not _str_or_none(record.get("cycle_id")):
        blockers.append("PAPER_EVIDENCE_CYCLE_ID_REQUIRED")
    payload = record.get("payload")
    if not isinstance(payload, dict):
        blockers.append("PAPER_EVIDENCE_PAYLOAD_MUST_BE_OBJECT")
    else:
        blockers.extend(_unsafe_payload_blockers("PAYLOAD", payload))
        expected_hash = stable_paper_evidence_payload_hash(payload)
        if record.get("payload_hash") != expected_hash:
            blockers.append("PAPER_EVIDENCE_PAYLOAD_HASH_MISMATCH")
    if record.get("paper_only") is not True:
        blockers.append("PAPER_EVIDENCE_RECORD_UNSAFE_PAPER_ONLY_FLAG")
    if record.get("read_only") is not True:
        blockers.append("PAPER_EVIDENCE_RECORD_UNSAFE_READ_ONLY_FLAG")
    if record.get("is_order_action") is not False:
        blockers.append("PAPER_EVIDENCE_RECORD_UNSAFE_ORDER_ACTION_FLAG")
    if record.get("broker_api_called") is not False:
        blockers.append("PAPER_EVIDENCE_RECORD_UNSAFE_BROKER_API_FLAG")
    if record.get("real_order_id") is not None:
        blockers.append("PAPER_EVIDENCE_RECORD_UNSAFE_REAL_ORDER_ID")
    return _dedupe(blockers)


def stable_paper_evidence_payload_hash(payload: dict[str, Any]) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _unsafe_payload_blockers(name: str, payload: Any) -> list[str]:
    if payload is None:
        return []
    if not isinstance(payload, dict):
        return [f"PAPER_EVIDENCE_{name}_MUST_BE_OBJECT"]
    blockers: list[str] = []
    for path, key, value in _walk_dict(payload):
        if key == "paper_only" and value is not True:
            blockers.append(f"PAPER_EVIDENCE_{name}_{path}_UNSAFE_PAPER_ONLY_FLAG")
        if key == "read_only" and value is not True:
            blockers.append(f"PAPER_EVIDENCE_{name}_{path}_UNSAFE_READ_ONLY_FLAG")
        if key == "is_order_action" and value is not False:
            blockers.append(f"PAPER_EVIDENCE_{name}_{path}_UNSAFE_ORDER_ACTION_FLAG")
        if key == "broker_api_called" and value is True:
            blockers.append(f"PAPER_EVIDENCE_{name}_{path}_BROKER_API_CALLED")
        if key == "real_order_id" and value not in (None, ""):
            blockers.append(f"PAPER_EVIDENCE_{name}_{path}_REAL_ORDER_ID_PRESENT")
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


def _normalize_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    if isinstance(path, Path):
        return str(path)
    if isinstance(path, str):
        text = path.strip()
        return text or None
    return None


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


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

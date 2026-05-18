from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from paper_trading.export_bundle import load_paper_export_manifest, validate_paper_export_bundle


PAPER_REPLAY_DATASET_SCHEMA_VERSION = "1.0"
PAPER_REPLAY_ROW_TYPE = "PAPER_REPLAY_DATASET_ROW"


class PaperReplayDatasetStatus(StrEnum):
    BUILT = "BUILT"
    VALID = "VALID"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperReplayDatasetResult:
    status: PaperReplayDatasetStatus
    bundle_root: str | None = None
    output_path: str | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    manifest: dict[str, Any] | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_REPLAY_DATASET_SCHEMA_VERSION

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
            "dataset_type": "PAPER_REPLAY_DATASET",
            "status": self.status.value,
            "bundle_root": self.bundle_root,
            "output_path": self.output_path,
            "row_count": self.row_count,
            "rows": deepcopy(self.rows),
            "manifest": deepcopy(self.manifest),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_replay_dataset_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_REPLAY_DATASET_SCHEMA_VERSION,
        "dataset_type": "PAPER_REPLAY_DATASET",
        "row_type": PAPER_REPLAY_ROW_TYPE,
        "output_format": "JSONL",
        "statuses": [status.value for status in PaperReplayDatasetStatus],
        "required_row_keys": [
            "schema_version",
            "row_type",
            "row_id",
            "source_bundle_id",
            "source_record_id",
            "source_record_type",
            "source_cycle_id",
            "source_candidate_id",
            "source_strategy_id",
            "source_created_at_epoch",
            "scenario_name",
            "event_count",
            "pipeline_status",
            "session_id",
            "payload_hash",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_result_keys": [
            "schema_version",
            "dataset_type",
            "status",
            "bundle_root",
            "output_path",
            "row_count",
            "rows",
            "manifest",
            "blockers",
            "warnings",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "safe_flags": _safe_flags(),
        "scope_boundary": [
            "local_replay_dataset_only",
            "paper_evidence_only",
            "source_traceable_rows",
            "no_outcome_scoring",
            "no_model_features",
            "no_runtime_wiring",
            "no_api",
            "no_ui",
            "no_broker_execution",
            "no_live_orders",
            "no_strategy_work",
            "no_agent_system_work",
        ],
    }


def build_paper_replay_dataset(
    *,
    bundle_root: str | Path | None,
    output_path: str | Path | None = None,
) -> PaperReplayDatasetResult:
    bundle_text = _normalize_path(bundle_root)
    output_text = _normalize_path(output_path)
    input_blockers = validate_paper_replay_dataset_inputs(bundle_root=bundle_root, output_path=output_path)
    if input_blockers:
        return PaperReplayDatasetResult(
            status=PaperReplayDatasetStatus.BLOCKED,
            bundle_root=bundle_text,
            output_path=output_text,
            blockers=input_blockers,
        )

    validation = validate_paper_export_bundle(bundle_root).to_dict()
    if validation.get("status") == "BLOCKED":
        return PaperReplayDatasetResult(
            status=PaperReplayDatasetStatus.BLOCKED,
            bundle_root=bundle_text,
            output_path=output_text,
            blockers=_prefixed("BUNDLE_VALIDATION", validation.get("blockers") or ["PAPER_REPLAY_BUNDLE_VALIDATION_BLOCKED"]),
            warnings=validation.get("warnings") or [],
        )

    manifest_result = load_paper_export_manifest(bundle_root).to_dict()
    if manifest_result.get("status") == "BLOCKED":
        return PaperReplayDatasetResult(
            status=PaperReplayDatasetStatus.BLOCKED,
            bundle_root=bundle_text,
            output_path=output_text,
            blockers=_prefixed("MANIFEST", manifest_result.get("blockers") or ["PAPER_REPLAY_MANIFEST_BLOCKED"]),
            warnings=manifest_result.get("warnings") or [],
        )
    manifest = manifest_result.get("manifest") or {}
    evidence_path = _bundle_evidence_path(bundle_text, manifest)
    evidence_records, evidence_blockers = _load_exported_evidence_records(evidence_path)
    if evidence_blockers:
        return PaperReplayDatasetResult(
            status=PaperReplayDatasetStatus.BLOCKED,
            bundle_root=bundle_text,
            output_path=output_text,
            manifest=manifest,
            blockers=evidence_blockers,
        )

    rows: list[dict[str, Any]] = []
    for record in evidence_records:
        row = _record_to_replay_row(record, manifest)
        if row:
            rows.append(row)

    row_blockers = validate_paper_replay_dataset_rows(rows)
    if row_blockers:
        return PaperReplayDatasetResult(
            status=PaperReplayDatasetStatus.BLOCKED,
            bundle_root=bundle_text,
            output_path=output_text,
            rows=rows,
            row_count=len(rows),
            manifest=manifest,
            blockers=row_blockers,
        )

    if output_text:
        target = Path(output_text)
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_replay_rows(target, rows)

    status = PaperReplayDatasetStatus.BUILT if rows else PaperReplayDatasetStatus.EMPTY
    warnings = [] if rows else ["PAPER_REPLAY_DATASET_NO_ELIGIBLE_ROWS"]
    return PaperReplayDatasetResult(
        status=status,
        bundle_root=bundle_text,
        output_path=output_text,
        rows=rows,
        row_count=len(rows),
        manifest=manifest,
        warnings=warnings,
    )


def validate_paper_replay_dataset_rows(rows: list[dict[str, Any]] | None) -> list[str]:
    if rows is None:
        return ["PAPER_REPLAY_ROWS_REQUIRED"]
    if not isinstance(rows, list):
        return ["PAPER_REPLAY_ROWS_MUST_BE_LIST"]
    blockers: list[str] = []
    required = paper_replay_dataset_schema_contract()["required_row_keys"]
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            blockers.append(f"PAPER_REPLAY_ROW_{index}_MUST_BE_OBJECT")
            continue
        for key in required:
            if key not in row:
                blockers.append(f"PAPER_REPLAY_ROW_{index}_MISSING_{key.upper()}")
        blockers.extend(f"PAPER_REPLAY_ROW_{index}_{blocker}" for blocker in _unsafe_payload_blockers("ROW", row))
        blockers.extend(f"PAPER_REPLAY_ROW_{index}_{blocker}" for blocker in _forbidden_analysis_field_blockers(row))
        if row.get("schema_version") != PAPER_REPLAY_DATASET_SCHEMA_VERSION:
            blockers.append(f"PAPER_REPLAY_ROW_{index}_UNKNOWN_SCHEMA_VERSION")
        if row.get("row_type") != PAPER_REPLAY_ROW_TYPE:
            blockers.append(f"PAPER_REPLAY_ROW_{index}_TYPE_INVALID")
    return _dedupe(blockers)


def load_paper_replay_dataset_rows(path: str | Path | None) -> PaperReplayDatasetResult:
    path_text = _normalize_path(path)
    if not path_text:
        return PaperReplayDatasetResult(status=PaperReplayDatasetStatus.BLOCKED, output_path=path_text, blockers=["PAPER_REPLAY_DATASET_PATH_REQUIRED"])
    source = Path(path_text)
    if not source.exists():
        return PaperReplayDatasetResult(status=PaperReplayDatasetStatus.EMPTY, output_path=str(source), warnings=["PAPER_REPLAY_DATASET_FILE_MISSING_EMPTY"])
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                blockers.append(f"PAPER_REPLAY_CORRUPT_JSONL_LINE_{line_no}")
                continue
            if not isinstance(parsed, dict):
                blockers.append(f"PAPER_REPLAY_NON_OBJECT_JSONL_LINE_{line_no}")
                continue
            rows.append(parsed)
    row_blockers = validate_paper_replay_dataset_rows(rows)
    blockers.extend(row_blockers)
    if blockers:
        return PaperReplayDatasetResult(
            status=PaperReplayDatasetStatus.BLOCKED,
            output_path=str(source),
            blockers=_dedupe(blockers),
        )
    return PaperReplayDatasetResult(
        status=PaperReplayDatasetStatus.VALID if rows else PaperReplayDatasetStatus.EMPTY,
        output_path=str(source),
        rows=rows,
        row_count=len(rows),
        warnings=[] if rows else ["PAPER_REPLAY_DATASET_FILE_EMPTY"],
    )


def stable_replay_row_id(row_seed: dict[str, Any]) -> str:
    return f"paper-replay-row-{sha256(_canonical_json(row_seed).encode('utf-8')).hexdigest()[:16]}"


def validate_paper_replay_dataset_inputs(*, bundle_root: str | Path | None, output_path: str | Path | None = None) -> list[str]:
    blockers: list[str] = []
    bundle_text = _normalize_path(bundle_root)
    output_text = _normalize_path(output_path)
    if not bundle_text:
        blockers.append("PAPER_REPLAY_BUNDLE_ROOT_REQUIRED")
    if output_path is not None and not output_text:
        blockers.append("PAPER_REPLAY_OUTPUT_PATH_INVALID")
    if bundle_text and output_text:
        bundle_path = Path(bundle_text).resolve()
        target_path = Path(output_text).resolve()
        if target_path == bundle_path or bundle_path in target_path.parents:
            blockers.append("PAPER_REPLAY_OUTPUT_PATH_MUST_NOT_MUTATE_BUNDLE")
    return _dedupe(blockers)


def _record_to_replay_row(record: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    blockers = _unsafe_payload_blockers("SOURCE_RECORD", record)
    blockers.extend(_forbidden_analysis_field_blockers(record))
    if blockers:
        return None
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    source_record_id = record.get("record_id")
    row_seed = {
        "bundle_id": manifest.get("bundle_id"),
        "record_id": source_record_id,
        "payload_hash": record.get("payload_hash"),
    }
    return {
        "schema_version": PAPER_REPLAY_DATASET_SCHEMA_VERSION,
        "row_type": PAPER_REPLAY_ROW_TYPE,
        "row_id": stable_replay_row_id(row_seed),
        "source_bundle_id": manifest.get("bundle_id"),
        "source_record_id": source_record_id,
        "source_record_type": record.get("record_type"),
        "source_cycle_id": record.get("cycle_id"),
        "source_candidate_id": record.get("candidate_id") or payload.get("candidate_id"),
        "source_strategy_id": record.get("strategy_id") or payload.get("strategy_id"),
        "source_created_at_epoch": record.get("created_at_epoch"),
        "scenario_name": payload.get("scenario_name"),
        "event_count": payload.get("event_count"),
        "pipeline_status": payload.get("status") or payload.get("pipeline_status"),
        "session_id": payload.get("session_id"),
        "payload_hash": record.get("payload_hash"),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _bundle_evidence_path(bundle_root: str | None, manifest: dict[str, Any]) -> Path:
    root = Path(bundle_root or "")
    files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
    rel_path = files.get("evidence") or "evidence/paper_evidence.jsonl"
    return root / str(rel_path)


def _load_exported_evidence_records(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], ["PAPER_REPLAY_EVIDENCE_FILE_MISSING"]
    records: list[dict[str, Any]] = []
    blockers: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                blockers.append(f"PAPER_REPLAY_EVIDENCE_CORRUPT_JSONL_LINE_{line_no}")
                continue
            if not isinstance(parsed, dict):
                blockers.append(f"PAPER_REPLAY_EVIDENCE_NON_OBJECT_JSONL_LINE_{line_no}")
                continue
            record_blockers = _unsafe_payload_blockers("EVIDENCE_RECORD", parsed)
            record_blockers.extend(_forbidden_analysis_field_blockers(parsed))
            if record_blockers:
                blockers.extend(f"LINE_{line_no}_{blocker}" for blocker in record_blockers)
                continue
            records.append(parsed)
    return records, _dedupe(blockers)


def _write_replay_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(_canonical_json(row) + "\n")


def _unsafe_payload_blockers(name: str, payload: Any) -> list[str]:
    if payload is None:
        return []
    if not isinstance(payload, dict):
        return [f"PAPER_REPLAY_{name}_MUST_BE_OBJECT"]
    blockers: list[str] = []
    for path, key, value in _walk_dict(payload):
        if key == "paper_only" and value is not True:
            blockers.append(f"PAPER_REPLAY_{name}_{path}_UNSAFE_PAPER_ONLY_FLAG")
        if key == "read_only" and value is not True:
            blockers.append(f"PAPER_REPLAY_{name}_{path}_UNSAFE_READ_ONLY_FLAG")
        if key == "is_order_action" and value is not False:
            blockers.append(f"PAPER_REPLAY_{name}_{path}_UNSAFE_ORDER_ACTION_FLAG")
        if key == "broker_api_called" and value is True:
            blockers.append(f"PAPER_REPLAY_{name}_{path}_BROKER_API_CALLED")
        if key == "real_order_id" and value not in (None, ""):
            blockers.append(f"PAPER_REPLAY_{name}_{path}_REAL_ORDER_ID_PRESENT")
    return blockers


def _forbidden_analysis_field_blockers(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    forbidden = {"expectancy", "profitability", "reward", "label", "labels", "future_return", "win_loss", "pnl_label"}
    blockers: list[str] = []
    for path, key, _value in _walk_dict(payload):
        lowered = key.lower()
        if lowered in forbidden:
            blockers.append(f"PAPER_REPLAY_{path}_ANALYSIS_FIELD_FORBIDDEN")
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


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _prefixed(source: str, blockers: list[str]) -> list[str]:
    return [f"PAPER_REPLAY_{source}_{blocker}" for blocker in blockers]


def _safe_flags() -> dict[str, Any]:
    return {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

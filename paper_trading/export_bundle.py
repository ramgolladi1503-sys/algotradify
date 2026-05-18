from __future__ import annotations

import json
import shutil
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from paper_trading.persistence import load_paper_evidence_records


PAPER_EXPORT_BUNDLE_SCHEMA_VERSION = "1.0"
PAPER_EXPORT_BUNDLE_TYPE = "PAPER_EVIDENCE_EXPORT_BUNDLE"


class PaperExportBundleStatus(StrEnum):
    BUILT = "BUILT"
    VALID = "VALID"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperExportBundleResult:
    status: PaperExportBundleStatus
    bundle_root: str | None = None
    manifest: dict[str, Any] | None = None
    files: dict[str, str] = field(default_factory=dict)
    checksums: dict[str, str] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_EXPORT_BUNDLE_SCHEMA_VERSION

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
            "bundle_type": PAPER_EXPORT_BUNDLE_TYPE,
            "status": self.status.value,
            "bundle_root": self.bundle_root,
            "manifest": deepcopy(self.manifest),
            "files": dict(self.files),
            "checksums": dict(self.checksums),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_export_bundle_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_EXPORT_BUNDLE_SCHEMA_VERSION,
        "bundle_type": PAPER_EXPORT_BUNDLE_TYPE,
        "statuses": [status.value for status in PaperExportBundleStatus],
        "bundle_layout": {
            "manifest": "manifest.json",
            "checksums": "checksums.json",
            "evidence": "evidence/paper_evidence.jsonl",
            "scenarios": "scenarios/scenario_results.json",
        },
        "required_manifest_keys": [
            "schema_version",
            "bundle_type",
            "bundle_id",
            "created_at_epoch",
            "source_evidence_path",
            "record_count",
            "scenario_count",
            "files",
            "checksums",
            "safe_flags",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_result_keys": [
            "schema_version",
            "bundle_type",
            "status",
            "bundle_root",
            "manifest",
            "files",
            "checksums",
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
            "local_bundle_only",
            "paper_evidence_only",
            "no_replay_dataset",
            "no_expectancy_scoring",
            "no_runtime_wiring",
            "no_api",
            "no_ui",
            "no_broker_execution",
            "no_live_orders",
            "no_strategy_work",
            "no_cloud_upload",
        ],
    }


def build_paper_export_bundle(
    *,
    bundle_root: str | Path | None,
    evidence_path: str | Path | None,
    scenario_results: list[dict[str, Any]] | None = None,
    created_at_epoch: float | None = None,
) -> PaperExportBundleResult:
    blockers = validate_paper_export_bundle_inputs(
        bundle_root=bundle_root,
        evidence_path=evidence_path,
        scenario_results=scenario_results,
    )
    bundle_text = _normalize_path(bundle_root)
    if blockers:
        return PaperExportBundleResult(
            status=PaperExportBundleStatus.BLOCKED,
            bundle_root=bundle_text,
            blockers=blockers,
        )

    evidence_load = load_paper_evidence_records(evidence_path)
    evidence_payload = evidence_load.to_dict()
    if evidence_payload.get("status") == "BLOCKED":
        return PaperExportBundleResult(
            status=PaperExportBundleStatus.BLOCKED,
            bundle_root=bundle_text,
            blockers=_prefixed("EVIDENCE_LOAD", evidence_payload.get("blockers") or ["PAPER_EXPORT_EVIDENCE_LOAD_BLOCKED"]),
            warnings=evidence_payload.get("warnings") or [],
        )
    evidence_records = evidence_payload.get("records") or []
    evidence_blockers = _validate_records_safe(evidence_records, source="EVIDENCE")
    if evidence_blockers:
        return PaperExportBundleResult(
            status=PaperExportBundleStatus.BLOCKED,
            bundle_root=bundle_text,
            blockers=evidence_blockers,
            warnings=evidence_payload.get("warnings") or [],
        )
    scenario_blockers = _validate_scenario_results(scenario_results or [])
    if scenario_blockers:
        return PaperExportBundleResult(
            status=PaperExportBundleStatus.BLOCKED,
            bundle_root=bundle_text,
            blockers=scenario_blockers,
        )

    root = Path(str(bundle_text))
    evidence_dir = root / "evidence"
    scenarios_dir = root / "scenarios"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    evidence_out = evidence_dir / "paper_evidence.jsonl"
    scenario_out = scenarios_dir / "scenario_results.json"
    checksums_out = root / "checksums.json"
    manifest_out = root / "manifest.json"

    _write_evidence_jsonl(evidence_out, evidence_records)
    _write_json(scenario_out, scenario_results or [])

    files = {
        "evidence": "evidence/paper_evidence.jsonl",
        "scenarios": "scenarios/scenario_results.json",
        "checksums": "checksums.json",
        "manifest": "manifest.json",
    }
    checksums = {
        files["evidence"]: stable_file_hash(evidence_out),
        files["scenarios"]: stable_file_hash(scenario_out),
    }
    _write_json(checksums_out, checksums)
    checksums[files["checksums"]] = stable_file_hash(checksums_out)

    manifest = _build_manifest(
        bundle_root=root,
        evidence_path=evidence_path,
        evidence_records=evidence_records,
        scenario_results=scenario_results or [],
        files=files,
        checksums=checksums,
        created_at_epoch=created_at_epoch,
    )
    _write_json(manifest_out, manifest)
    checksums[files["manifest"]] = stable_file_hash(manifest_out)
    manifest["checksums"] = dict(checksums)
    _write_json(manifest_out, manifest)

    validation = validate_paper_export_bundle(root).to_dict()
    if validation["status"] == "BLOCKED":
        return PaperExportBundleResult(
            status=PaperExportBundleStatus.BLOCKED,
            bundle_root=str(root),
            manifest=manifest,
            files=files,
            checksums=checksums,
            blockers=_prefixed("VALIDATION", validation.get("blockers") or ["PAPER_EXPORT_VALIDATION_BLOCKED"]),
        )

    return PaperExportBundleResult(
        status=PaperExportBundleStatus.BUILT,
        bundle_root=str(root),
        manifest=manifest,
        files=files,
        checksums=checksums,
        warnings=evidence_payload.get("warnings") or [],
    )


def validate_paper_export_bundle(bundle_root: str | Path | None) -> PaperExportBundleResult:
    root_text = _normalize_path(bundle_root)
    if not root_text:
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, blockers=["PAPER_EXPORT_BUNDLE_ROOT_REQUIRED"])
    root = Path(root_text)
    manifest_path = root / "manifest.json"
    checksums_path = root / "checksums.json"
    blockers: list[str] = []
    if not manifest_path.exists():
        blockers.append("PAPER_EXPORT_MANIFEST_MISSING")
    if not checksums_path.exists():
        blockers.append("PAPER_EXPORT_CHECKSUMS_MISSING")
    if blockers:
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=str(root), blockers=blockers)

    manifest = load_paper_export_manifest(root).to_dict()
    if manifest["status"] == "BLOCKED":
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=str(root), blockers=_prefixed("MANIFEST", manifest.get("blockers") or []))
    manifest_payload = manifest.get("manifest") or {}
    manifest_blockers = _validate_manifest(manifest_payload)
    if manifest_blockers:
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=str(root), manifest=manifest_payload, blockers=manifest_blockers)

    try:
        checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=str(root), manifest=manifest_payload, blockers=["PAPER_EXPORT_CHECKSUMS_CORRUPT"])
    if not isinstance(checksums, dict):
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=str(root), manifest=manifest_payload, blockers=["PAPER_EXPORT_CHECKSUMS_MUST_BE_OBJECT"])

    files = manifest_payload.get("files") if isinstance(manifest_payload.get("files"), dict) else {}
    checksum_blockers: list[str] = []
    for label, rel_path in files.items():
        file_path = root / str(rel_path)
        if not file_path.exists():
            checksum_blockers.append(f"PAPER_EXPORT_FILE_MISSING_{str(label).upper()}")
            continue
        expected = checksums.get(str(rel_path)) or manifest_payload.get("checksums", {}).get(str(rel_path))
        actual = stable_file_hash(file_path)
        if expected and expected != actual:
            checksum_blockers.append(f"PAPER_EXPORT_CHECKSUM_MISMATCH_{str(label).upper()}")
    if checksum_blockers:
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=str(root), manifest=manifest_payload, files=files, checksums=checksums, blockers=checksum_blockers)

    forbidden = ["replay_dataset.json", "replay_dataset.jsonl", "expectancy.json", "profitability.json"]
    for name in forbidden:
        if (root / name).exists():
            return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=str(root), manifest=manifest_payload, files=files, checksums=checksums, blockers=[f"PAPER_EXPORT_FORBIDDEN_FILE_{name.upper().replace('.', '_')}"])

    return PaperExportBundleResult(
        status=PaperExportBundleStatus.VALID,
        bundle_root=str(root),
        manifest=manifest_payload,
        files=files,
        checksums=checksums,
    )


def load_paper_export_manifest(bundle_root: str | Path | None) -> PaperExportBundleResult:
    root_text = _normalize_path(bundle_root)
    if not root_text:
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, blockers=["PAPER_EXPORT_BUNDLE_ROOT_REQUIRED"])
    manifest_path = Path(root_text) / "manifest.json"
    if not manifest_path.exists():
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=root_text, blockers=["PAPER_EXPORT_MANIFEST_MISSING"])
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=root_text, blockers=["PAPER_EXPORT_MANIFEST_CORRUPT"])
    if not isinstance(manifest, dict):
        return PaperExportBundleResult(status=PaperExportBundleStatus.BLOCKED, bundle_root=root_text, blockers=["PAPER_EXPORT_MANIFEST_MUST_BE_OBJECT"])
    return PaperExportBundleResult(status=PaperExportBundleStatus.VALID, bundle_root=root_text, manifest=manifest)


def validate_paper_export_bundle_inputs(
    *,
    bundle_root: str | Path | None,
    evidence_path: str | Path | None,
    scenario_results: list[dict[str, Any]] | None = None,
) -> list[str]:
    blockers: list[str] = []
    if not _normalize_path(bundle_root):
        blockers.append("PAPER_EXPORT_BUNDLE_ROOT_REQUIRED")
    if not _normalize_path(evidence_path):
        blockers.append("PAPER_EXPORT_EVIDENCE_PATH_REQUIRED")
    if scenario_results is not None and not isinstance(scenario_results, list):
        blockers.append("PAPER_EXPORT_SCENARIO_RESULTS_MUST_BE_LIST")
    elif scenario_results:
        blockers.extend(_validate_scenario_results(scenario_results))
    return _dedupe(blockers)


def stable_file_hash(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _build_manifest(
    *,
    bundle_root: Path,
    evidence_path: str | Path | None,
    evidence_records: list[dict[str, Any]],
    scenario_results: list[dict[str, Any]],
    files: dict[str, str],
    checksums: dict[str, str],
    created_at_epoch: float | None,
) -> dict[str, Any]:
    bundle_seed = _canonical_json(
        {
            "evidence_hashes": [record.get("payload_hash") for record in evidence_records],
            "scenario_names": [result.get("scenario_name") for result in scenario_results],
            "created_at_epoch": created_at_epoch,
        }
    )
    return {
        "schema_version": PAPER_EXPORT_BUNDLE_SCHEMA_VERSION,
        "bundle_type": PAPER_EXPORT_BUNDLE_TYPE,
        "bundle_id": f"paper-export-{sha256(bundle_seed.encode('utf-8')).hexdigest()[:16]}",
        "created_at_epoch": created_at_epoch,
        "source_evidence_path": _normalize_path(evidence_path),
        "record_count": len(evidence_records),
        "scenario_count": len(scenario_results),
        "files": dict(files),
        "checksums": dict(checksums),
        "safe_flags": _safe_flags(),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _validate_manifest(manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key in paper_export_bundle_schema_contract()["required_manifest_keys"]:
        if key not in manifest:
            blockers.append(f"PAPER_EXPORT_MANIFEST_MISSING_{key.upper()}")
    if manifest.get("schema_version") != PAPER_EXPORT_BUNDLE_SCHEMA_VERSION:
        blockers.append("PAPER_EXPORT_UNKNOWN_SCHEMA_VERSION")
    if manifest.get("bundle_type") != PAPER_EXPORT_BUNDLE_TYPE:
        blockers.append("PAPER_EXPORT_BUNDLE_TYPE_INVALID")
    blockers.extend(_unsafe_payload_blockers("MANIFEST", manifest))
    if "replay" in _canonical_json(manifest.get("files") or {}).lower():
        blockers.append("PAPER_EXPORT_REPLAY_DATASET_FORBIDDEN")
    if "expectancy" in _canonical_json(manifest).lower() or "profitability" in _canonical_json(manifest).lower():
        blockers.append("PAPER_EXPORT_EXPECTANCY_PROFITABILITY_FORBIDDEN")
    return _dedupe(blockers)


def _validate_records_safe(records: list[Any], *, source: str) -> list[str]:
    blockers: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            blockers.append(f"PAPER_EXPORT_{source}_{index}_RECORD_MUST_BE_OBJECT")
            continue
        blockers.extend(f"PAPER_EXPORT_{source}_{index}_{blocker}" for blocker in _unsafe_payload_blockers("RECORD", record))
    return _dedupe(blockers)


def _validate_scenario_results(results: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for index, result in enumerate(results):
        if not isinstance(result, dict):
            blockers.append(f"PAPER_EXPORT_SCENARIO_{index}_MUST_BE_OBJECT")
            continue
        blockers.extend(f"PAPER_EXPORT_SCENARIO_{index}_{blocker}" for blocker in _unsafe_payload_blockers("RESULT", result))
        text = _canonical_json(result).lower()
        if "replay_dataset" in text:
            blockers.append(f"PAPER_EXPORT_SCENARIO_{index}_REPLAY_DATASET_FORBIDDEN")
        if "expectancy" in text or "profitability" in text:
            blockers.append(f"PAPER_EXPORT_SCENARIO_{index}_EXPECTANCY_PROFITABILITY_FORBIDDEN")
    return _dedupe(blockers)


def _write_evidence_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(_canonical_json(record) + "\n")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _unsafe_payload_blockers(name: str, payload: Any) -> list[str]:
    if payload is None:
        return []
    if not isinstance(payload, dict):
        return [f"PAPER_EXPORT_{name}_MUST_BE_OBJECT"]
    blockers: list[str] = []
    for path, key, value in _walk_dict(payload):
        if key == "paper_only" and value is not True:
            blockers.append(f"PAPER_EXPORT_{name}_{path}_UNSAFE_PAPER_ONLY_FLAG")
        if key == "read_only" and value is not True:
            blockers.append(f"PAPER_EXPORT_{name}_{path}_UNSAFE_READ_ONLY_FLAG")
        if key == "is_order_action" and value is not False:
            blockers.append(f"PAPER_EXPORT_{name}_{path}_UNSAFE_ORDER_ACTION_FLAG")
        if key == "broker_api_called" and value is True:
            blockers.append(f"PAPER_EXPORT_{name}_{path}_BROKER_API_CALLED")
        if key == "real_order_id" and value not in (None, ""):
            blockers.append(f"PAPER_EXPORT_{name}_{path}_REAL_ORDER_ID_PRESENT")
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
    return [f"PAPER_EXPORT_{source}_{blocker}" for blocker in blockers]


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

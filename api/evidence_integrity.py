from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.evidence_schema_registry import EvidenceSchema, get_evidence_schema


@dataclass(frozen=True)
class EvidenceIntegrityResult:
    valid: bool
    schema_id: str
    missing_keys: list[str] = field(default_factory=list)
    safe_flag_violations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "schema_id": self.schema_id,
            "missing_keys": list(self.missing_keys),
            "safe_flag_violations": list(self.safe_flag_violations),
            "warnings": list(self.warnings),
        }


def validate_evidence_payload(schema_id: str, payload: dict[str, Any]) -> EvidenceIntegrityResult:
    schema = get_evidence_schema(schema_id)
    return validate_evidence_payload_against_schema(schema, payload)


def validate_evidence_payload_against_schema(schema: EvidenceSchema, payload: dict[str, Any]) -> EvidenceIntegrityResult:
    if not isinstance(payload, dict):
        return EvidenceIntegrityResult(
            valid=False,
            schema_id=schema.schema_id,
            missing_keys=sorted(schema.required_keys),
            warnings=["payload is not a dictionary"],
        )

    missing_keys = sorted(key for key in schema.required_keys if key not in payload)
    safe_flag_violations = _safe_flag_violations(schema.safe_flags, payload)
    warnings = _integrity_warnings(schema, payload)
    return EvidenceIntegrityResult(
        valid=not missing_keys and not safe_flag_violations,
        schema_id=schema.schema_id,
        missing_keys=missing_keys,
        safe_flag_violations=safe_flag_violations,
        warnings=warnings,
    )


def validate_many_evidence_payloads(items: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        schema_id: validate_evidence_payload(schema_id, payload).to_dict()
        for schema_id, payload in sorted(items.items())
    }


def _safe_flag_violations(safe_flags: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for key, expected in sorted(safe_flags.items()):
        actual = payload.get(key)
        if actual is not expected:
            violations.append({"key": key, "expected": expected, "actual": actual})
    return violations


def _integrity_warnings(schema: EvidenceSchema, payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    schema_version = payload.get("schema_version")
    if schema_version is not None and schema_version not in schema.compatible_schema_versions:
        warnings.append(
            f"schema_version {schema_version!r} is not compatible with {list(schema.compatible_schema_versions)!r}"
        )
    evidence_type = payload.get("evidence_type") or payload.get("bundle_type")
    if evidence_type is not None and evidence_type != schema.evidence_type:
        warnings.append(f"evidence_type {evidence_type!r} does not match {schema.evidence_type!r}")
    return warnings

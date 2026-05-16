from __future__ import annotations

import pytest

from api.evidence_integrity import (
    EvidenceIntegrityResult,
    validate_evidence_payload,
    validate_evidence_payload_against_schema,
    validate_many_evidence_payloads,
)
from api.evidence_schema_registry import get_evidence_schema


def _valid_export_bundle() -> dict:
    return {
        "bundle_type": "DRY_RUN_EVIDENCE_BUNDLE",
        "schema_version": "1.0",
        "created": True,
        "candidate_id": "c1",
        "dry_run_order_id": "dry-run-1",
        "dry_run_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "status": "BUNDLE_READY",
        "blockers": [],
        "warnings": [],
        "selected_candidate_snapshot": {},
        "execution_safety_snapshot": {},
        "approval_snapshot": {},
        "readiness_snapshot": {},
        "dry_run_intent": {},
        "lifecycle_event": {},
        "outcome_event": {},
        "export_preview_only": True,
    }


def test_validate_evidence_payload_accepts_valid_export_bundle():
    result = validate_evidence_payload("dry_run_export_bundle", _valid_export_bundle())

    assert result.valid is True
    assert result.schema_id == "dry_run_export_bundle"
    assert result.missing_keys == []
    assert result.safe_flag_violations == []
    assert result.warnings == []
    assert result.to_dict() == {
        "valid": True,
        "schema_id": "dry_run_export_bundle",
        "missing_keys": [],
        "safe_flag_violations": [],
        "warnings": [],
    }


def test_validate_evidence_payload_reports_missing_keys():
    payload = _valid_export_bundle()
    del payload["dry_run_intent"]
    del payload["lifecycle_event"]

    result = validate_evidence_payload("dry_run_export_bundle", payload)

    assert result.valid is False
    assert result.missing_keys == ["dry_run_intent", "lifecycle_event"]
    assert result.safe_flag_violations == []


def test_validate_evidence_payload_reports_safe_flag_violations():
    payload = _valid_export_bundle()
    payload["dry_run_only"] = False
    payload["broker_api_called"] = True
    payload["real_order_id"] = "REAL-1"

    result = validate_evidence_payload("dry_run_export_bundle", payload)

    assert result.valid is False
    assert result.missing_keys == []
    assert {row["key"] for row in result.safe_flag_violations} == {
        "dry_run_only",
        "broker_api_called",
        "real_order_id",
    }
    assert {row["key"]: row["expected"] for row in result.safe_flag_violations} == {
        "dry_run_only": True,
        "broker_api_called": False,
        "real_order_id": None,
    }


def test_validate_evidence_payload_warns_on_incompatible_schema_version():
    payload = _valid_export_bundle()
    payload["schema_version"] = "9.9"

    result = validate_evidence_payload("dry_run_export_bundle", payload)

    assert result.valid is True
    assert result.warnings == ["schema_version '9.9' is not compatible with ['1.0']"]


def test_validate_evidence_payload_warns_on_wrong_evidence_type():
    payload = _valid_export_bundle()
    payload["bundle_type"] = "WRONG_BUNDLE"

    result = validate_evidence_payload("dry_run_export_bundle", payload)

    assert result.valid is True
    assert result.warnings == ["evidence_type 'WRONG_BUNDLE' does not match 'DRY_RUN_EVIDENCE_BUNDLE'"]


def test_validate_evidence_payload_against_schema_rejects_non_dict_payload():
    schema = get_evidence_schema("approval_evidence")

    result = validate_evidence_payload_against_schema(schema, ["not", "a", "dict"])  # type: ignore[arg-type]

    assert result.valid is False
    assert result.schema_id == "approval_evidence"
    assert "payload is not a dictionary" in result.warnings
    assert "approval_id" in result.missing_keys
    assert "candidate_id" in result.missing_keys


def test_validate_many_evidence_payloads_returns_sorted_dict_results():
    results = validate_many_evidence_payloads(
        {
            "dry_run_export_bundle": _valid_export_bundle(),
            "readiness_snapshot": {"candidate_id": "c1", "execution_allowed": True},
        }
    )

    assert list(results) == ["dry_run_export_bundle", "readiness_snapshot"]
    assert results["dry_run_export_bundle"]["valid"] is True
    assert results["readiness_snapshot"]["valid"] is True


def test_validate_evidence_payload_rejects_unknown_schema_id():
    with pytest.raises(KeyError, match="unknown evidence schema"):
        validate_evidence_payload("missing_schema", {})


def test_integrity_result_serializes_lists_defensively():
    result = EvidenceIntegrityResult(
        valid=False,
        schema_id="x",
        missing_keys=["a"],
        safe_flag_violations=[{"key": "dry_run_only", "expected": True, "actual": False}],
        warnings=["warn"],
    )

    serialized = result.to_dict()
    serialized["missing_keys"].append("mutated")

    assert result.missing_keys == ["a"]

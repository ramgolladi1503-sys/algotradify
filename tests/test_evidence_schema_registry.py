from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.dry_run_execution_route import dry_run_export_schema_contract
from api.evidence_schema_registry import (
    EVIDENCE_SCHEMA_REGISTRY,
    SCHEMA_VERSION_1,
    evidence_schema_registry_snapshot,
    get_evidence_schema,
    list_evidence_schema_ids,
)


SNAPSHOT_PATH = Path(__file__).resolve().parent / "fixtures" / "evidence_schema_registry_snapshot.json"

EXPECTED_SCHEMA_IDS = {
    "dry_run_export_bundle",
    "dry_run_execution_payload",
    "execution_safety_decision",
    "approval_evidence",
    "readiness_snapshot",
    "lifecycle_event",
    "outcome_replay_event",
}


def _registry_snapshot_fixture() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_evidence_schema_registry_exposes_expected_schema_ids():
    assert set(list_evidence_schema_ids()) == EXPECTED_SCHEMA_IDS
    assert set(EVIDENCE_SCHEMA_REGISTRY) == EXPECTED_SCHEMA_IDS


def test_evidence_schema_registry_contracts_are_stable_and_discoverable():
    snapshot = evidence_schema_registry_snapshot()

    assert set(snapshot) == EXPECTED_SCHEMA_IDS
    for schema_id, contract in snapshot.items():
        assert contract["schema_id"] == schema_id
        assert contract["evidence_type"]
        assert contract["schema_version"] == SCHEMA_VERSION_1
        assert contract["compatible_schema_versions"] == [SCHEMA_VERSION_1]
        assert contract["required_keys"] == sorted(contract["required_keys"])
        assert contract["required_keys"]
        assert isinstance(contract["safe_flags"], dict)
        assert contract["description"]


def test_evidence_schema_registry_snapshot_matches_fixture():
    assert evidence_schema_registry_snapshot() == _registry_snapshot_fixture()


def test_evidence_schema_registry_snapshot_order_is_deterministic():
    snapshot = evidence_schema_registry_snapshot()

    assert list(snapshot) == sorted(snapshot)
    for contract in snapshot.values():
        assert contract["required_keys"] == sorted(contract["required_keys"])


def test_dry_run_export_bundle_registry_matches_route_contract():
    registry_contract = get_evidence_schema("dry_run_export_bundle").to_contract()
    route_contract = dry_run_export_schema_contract()

    assert registry_contract["evidence_type"] == route_contract["bundle_type"]
    assert registry_contract["schema_version"] == route_contract["schema_version"]
    assert registry_contract["compatible_schema_versions"] == route_contract["compatible_schema_versions"]
    assert registry_contract["required_keys"] == route_contract["required_keys"]
    assert registry_contract["safe_flags"] == route_contract["safe_flags"]


def test_registry_safe_flags_keep_no_order_boundaries():
    snapshot = evidence_schema_registry_snapshot()

    assert snapshot["dry_run_export_bundle"]["safe_flags"] == {
        "dry_run_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "export_preview_only": True,
    }
    assert snapshot["dry_run_execution_payload"]["safe_flags"] == {
        "dry_run_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    assert snapshot["execution_safety_decision"]["safe_flags"]["is_order_action"] is False
    assert snapshot["approval_evidence"]["safe_flags"]["is_order_action"] is False
    assert snapshot["lifecycle_event"]["safe_flags"]["broker_api_called"] is False
    assert snapshot["outcome_replay_event"]["safe_flags"]["real_order_id"] is None


def test_registry_required_keys_cover_core_evidence_chain():
    snapshot = evidence_schema_registry_snapshot()

    assert "dry_run_intent" in snapshot["dry_run_export_bundle"]["required_keys"]
    assert "lifecycle_event" in snapshot["dry_run_export_bundle"]["required_keys"]
    assert "outcome_event" in snapshot["dry_run_export_bundle"]["required_keys"]
    assert "execution_permitted" in snapshot["execution_safety_decision"]["required_keys"]
    assert "approval_id" in snapshot["approval_evidence"]["required_keys"]
    assert "execution_allowed" in snapshot["readiness_snapshot"]["required_keys"]
    assert "broker_api_called" in snapshot["lifecycle_event"]["required_keys"]
    assert "evidence" in snapshot["outcome_replay_event"]["required_keys"]


def test_get_evidence_schema_rejects_unknown_schema_id():
    with pytest.raises(KeyError, match="unknown evidence schema"):
        get_evidence_schema("missing_schema")

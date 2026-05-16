from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dry_run_execution_route import (
    DRY_RUN_EXPORT_BUNDLE_TYPE,
    DRY_RUN_EXPORT_COMPATIBLE_SCHEMA_VERSIONS,
    DRY_RUN_EXPORT_REQUIRED_KEYS,
    DRY_RUN_EXPORT_SAFE_FLAGS,
    DRY_RUN_EXPORT_SCHEMA_VERSION,
    build_dry_run_export_bundle,
    dry_run_export_schema_contract,
    install_dry_run_execution_route,
)


REQUIRED_EXPORT_BUNDLE_KEYS = set(DRY_RUN_EXPORT_REQUIRED_KEYS)
SAFE_EXPORT_FLAGS = dict(DRY_RUN_EXPORT_SAFE_FLAGS)


def _assert_export_bundle_contract(bundle: dict):
    missing = REQUIRED_EXPORT_BUNDLE_KEYS - set(bundle)
    assert not missing, f"missing export bundle keys: {sorted(missing)}"
    assert bundle["bundle_type"] == DRY_RUN_EXPORT_BUNDLE_TYPE
    assert bundle["schema_version"] == DRY_RUN_EXPORT_SCHEMA_VERSION
    assert isinstance(bundle["created"], bool)
    assert isinstance(bundle["blockers"], list)
    assert isinstance(bundle["warnings"], list)
    assert isinstance(bundle["selected_candidate_snapshot"], dict)
    assert isinstance(bundle["execution_safety_snapshot"], dict)
    assert isinstance(bundle["approval_snapshot"], dict)
    assert isinstance(bundle["readiness_snapshot"], dict)
    assert isinstance(bundle["dry_run_intent"], dict)
    assert isinstance(bundle["lifecycle_event"], dict)
    assert isinstance(bundle["outcome_event"], dict)
    for key, expected in SAFE_EXPORT_FLAGS.items():
        assert bundle[key] is expected, f"{key} must remain {expected!r}"


def _top(candidate_id="c1"):
    return {
        "status": "SELECTED",
        "selected": {
            "candidate_id": candidate_id,
            "symbol": "NIFTY26MAY25500CE",
            "tradingsymbol": "NIFTY26MAY25500CE",
            "quality_score": 91,
            "is_order": False,
        },
        "is_order_action": False,
    }


def _readiness(candidate_id="c1"):
    return [{"candidate_id": candidate_id, "execution_allowed": True}]


def _safety(permitted=True):
    return {
        "execution_permitted": permitted,
        "status": "PERMITTED" if permitted else "BLOCKED",
        "is_order_action": False,
        "safety_visibility_only": True,
        "blockers": [] if permitted else ["TEST_BLOCKER"],
    }


def _approval(candidate_id="c1", status="APPROVED"):
    return {
        "candidate_id": candidate_id,
        "current_status": status,
        "approval_id": "approval-1234",
        "operator_id": "op1",
        "events": [
            {
                "approval_id": "approval-1234",
                "candidate_id": candidate_id,
                "operator_id": "op1",
                "status": status,
                "safety_decision": {"execution_permitted": True, "status": "PERMITTED", "is_order_action": False},
                "is_order_action": False,
            }
        ],
        "blockers": [],
        "is_order_action": False,
    }


def _matcher(top, readiness):
    selected = top.get("selected") if isinstance(top, dict) else None
    candidate_id = selected.get("candidate_id") if isinstance(selected, dict) else None
    for row in readiness:
        if row.get("candidate_id") == candidate_id:
            return row
    return None


def _client(tmp_path: Path, *, top=None, safety=None, approval=None):
    app = FastAPI()
    install_dry_run_execution_route(
        app,
        runtime_root_provider=lambda: tmp_path,
        top_executable_provider=lambda limit, min_quality_score: top if top is not None else _top(),
        readiness_provider=lambda limit: _readiness(),
        safety_provider=lambda request, limit, min_quality_score: safety if safety is not None else _safety(),
        approval_provider=lambda candidate_id, now_epoch: approval if approval is not None else _approval(candidate_id or "c1"),
        readiness_matcher=_matcher,
    )
    return TestClient(app)


def test_dry_run_execution_route_blocks_default_missing_evidence(tmp_path):
    client = _client(tmp_path, top={"status": "NONE"}, safety=_safety(False), approval={})

    response = client.get("/dry-run-execution")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is False
    assert payload["dry_run_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False
    assert "NO_TOP_EXECUTABLE_SELECTED" in payload["blockers"]
    assert "EXECUTION_SAFETY_NOT_PERMITTED" in payload["blockers"]
    assert "APPROVAL_EVIDENCE_REQUIRED" in payload["blockers"]


def test_dry_run_execution_route_creates_when_evidence_valid(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution?now_epoch=100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    assert payload["candidate_id"] == "c1"
    assert payload["intent"]["dry_run_only"] is True
    assert payload["intent"]["is_order_action"] is False
    assert payload["intent"]["broker_api_called"] is False
    assert payload["intent"]["real_order_id"] is None
    assert payload["lifecycle_event"]["status"] == "DRY_RUN_INTENT_CREATED"
    assert payload["outcome_event"]["evidence"]["dry_run_only"] is True


def test_dry_run_execution_route_append_false_writes_no_files(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution?now_epoch=100&append=false")

    assert response.status_code == 200
    assert response.json()["created"] is True
    assert not (tmp_path / "logs" / "dry_run_order_intents.jsonl").exists()
    assert not (tmp_path / "logs" / "dry_run_lifecycle.jsonl").exists()
    assert not (tmp_path / "logs" / "outcome_replay.jsonl").exists()


def test_dry_run_execution_route_append_true_writes_jsonl(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution?now_epoch=100&append=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    assert set(payload["append_paths"]) == {"intent", "lifecycle", "outcome"}
    intent_rows = [json.loads(line) for line in (tmp_path / "logs" / "dry_run_order_intents.jsonl").read_text(encoding="utf-8").splitlines()]
    lifecycle_rows = [json.loads(line) for line in (tmp_path / "logs" / "dry_run_lifecycle.jsonl").read_text(encoding="utf-8").splitlines()]
    outcome_rows = [json.loads(line) for line in (tmp_path / "logs" / "outcome_replay.jsonl").read_text(encoding="utf-8").splitlines()]
    assert intent_rows[0]["dry_run_only"] is True
    assert lifecycle_rows[0]["broker_api_called"] is False
    assert outcome_rows[0]["real_order_id"] is None


def test_dry_run_execution_route_always_exposes_safe_flags(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run_only"] is True
    assert payload["is_order_action"] is False
    assert payload["broker_api_called"] is False


def test_dry_run_export_bundle_shape_from_payload(tmp_path):
    client = _client(tmp_path)
    payload = client.get("/dry-run-execution?now_epoch=100").json()

    bundle = build_dry_run_export_bundle(payload)

    assert bundle["bundle_type"] == DRY_RUN_EXPORT_BUNDLE_TYPE
    assert bundle["schema_version"] == DRY_RUN_EXPORT_SCHEMA_VERSION
    assert bundle["status"] == "BUNDLE_READY"
    assert bundle["candidate_id"] == "c1"
    assert bundle["dry_run_only"] is True
    assert bundle["is_order_action"] is False
    assert bundle["broker_api_called"] is False
    assert bundle["real_order_id"] is None
    assert bundle["selected_candidate_snapshot"]["status"] == "SELECTED"
    assert bundle["execution_safety_snapshot"]["status"] == "PERMITTED"
    assert bundle["approval_snapshot"]["current_status"] == "APPROVED"
    assert bundle["readiness_snapshot"]["execution_allowed"] is True
    assert bundle["outcome_event"]["evidence"]["dry_run_only"] is True
    assert bundle["export_preview_only"] is True


def test_dry_run_execution_export_endpoint_returns_bundle_and_writes_no_files(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution/export?now_epoch=100")

    assert response.status_code == 200
    bundle = response.json()
    assert bundle["bundle_type"] == DRY_RUN_EXPORT_BUNDLE_TYPE
    assert bundle["status"] == "BUNDLE_READY"
    assert bundle["dry_run_only"] is True
    assert bundle["is_order_action"] is False
    assert bundle["broker_api_called"] is False
    assert bundle["real_order_id"] is None
    assert bundle["export_preview_only"] is True
    assert not (tmp_path / "logs" / "dry_run_order_intents.jsonl").exists()
    assert not (tmp_path / "logs" / "dry_run_lifecycle.jsonl").exists()
    assert not (tmp_path / "logs" / "outcome_replay.jsonl").exists()


def test_dry_run_execution_export_endpoint_blocks_safely_when_evidence_missing(tmp_path):
    client = _client(tmp_path, top={"status": "NONE"}, safety=_safety(False), approval={})

    response = client.get("/dry-run-execution/export")

    assert response.status_code == 200
    bundle = response.json()
    assert bundle["bundle_type"] == DRY_RUN_EXPORT_BUNDLE_TYPE
    assert bundle["status"] == "BUNDLE_BLOCKED"
    assert bundle["dry_run_only"] is True
    assert bundle["is_order_action"] is False
    assert bundle["broker_api_called"] is False
    assert "NO_TOP_EXECUTABLE_SELECTED" in bundle["blockers"]


def test_dry_run_export_bundle_contract_ready_shape_is_frozen(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution/export?now_epoch=100&limit=20")

    assert response.status_code == 200
    bundle = response.json()
    _assert_export_bundle_contract(bundle)
    assert set(bundle) == REQUIRED_EXPORT_BUNDLE_KEYS
    assert bundle["created"] is True
    assert bundle["status"] == "BUNDLE_READY"
    assert bundle["candidate_id"] == "c1"
    assert bundle["dry_run_order_id"]
    assert bundle["dry_run_intent"]["dry_run_only"] is True
    assert bundle["lifecycle_event"]["broker_api_called"] is False
    assert bundle["outcome_event"]["real_order_id"] is None


def test_dry_run_export_bundle_contract_blocked_shape_is_frozen(tmp_path):
    client = _client(tmp_path, top={"status": "NONE"}, safety=_safety(False), approval={})

    response = client.get("/dry-run-execution/export?limit=20")

    assert response.status_code == 200
    bundle = response.json()
    _assert_export_bundle_contract(bundle)
    assert set(bundle) == REQUIRED_EXPORT_BUNDLE_KEYS
    assert bundle["created"] is False
    assert bundle["status"] == "BUNDLE_BLOCKED"
    assert bundle["candidate_id"] is None
    assert bundle["dry_run_order_id"] is None
    assert "NO_TOP_EXECUTABLE_SELECTED" in bundle["blockers"]
    assert "EXECUTION_SAFETY_NOT_PERMITTED" in bundle["blockers"]
    assert "APPROVAL_EVIDENCE_REQUIRED" in bundle["blockers"]


def test_dry_run_export_ignores_append_true_and_writes_no_files(tmp_path):
    client = _client(tmp_path)

    response = client.get("/dry-run-execution/export?now_epoch=100&append=true")

    assert response.status_code == 200
    bundle = response.json()
    _assert_export_bundle_contract(bundle)
    assert bundle["status"] == "BUNDLE_READY"
    assert not (tmp_path / "logs" / "dry_run_order_intents.jsonl").exists()
    assert not (tmp_path / "logs" / "dry_run_lifecycle.jsonl").exists()
    assert not (tmp_path / "logs" / "outcome_replay.jsonl").exists()


def test_dry_run_export_bundle_builder_overrides_any_unsafe_payload_flags():
    bundle = build_dry_run_export_bundle(
        {
            "created": True,
            "candidate_id": "c-danger",
            "dry_run_only": False,
            "is_order_action": True,
            "broker_api_called": True,
            "real_order_id": "REAL-ORDER-1",
            "export_preview_only": False,
            "intent": {
                "candidate_id": "c-danger",
                "dry_run_order_id": "dry-run-1",
                "real_order_id": "REAL-ORDER-2",
                "broker_api_called": True,
                "is_order_action": True,
            },
        }
    )

    _assert_export_bundle_contract(bundle)
    assert bundle["candidate_id"] == "c-danger"
    assert bundle["dry_run_order_id"] == "dry-run-1"
    assert bundle["dry_run_only"] is True
    assert bundle["is_order_action"] is False
    assert bundle["broker_api_called"] is False
    assert bundle["real_order_id"] is None
    assert bundle["export_preview_only"] is True


def test_dry_run_export_schema_version_contract_is_explicit():
    contract = dry_run_export_schema_contract()

    assert contract["bundle_type"] == DRY_RUN_EXPORT_BUNDLE_TYPE
    assert contract["schema_version"] == "1.0"
    assert contract["schema_version"] == DRY_RUN_EXPORT_SCHEMA_VERSION
    assert contract["compatible_schema_versions"] == list(DRY_RUN_EXPORT_COMPATIBLE_SCHEMA_VERSIONS)
    assert DRY_RUN_EXPORT_COMPATIBLE_SCHEMA_VERSIONS == ("1.0",)
    assert set(contract["required_keys"]) == DRY_RUN_EXPORT_REQUIRED_KEYS
    assert contract["safe_flags"] == DRY_RUN_EXPORT_SAFE_FLAGS


def test_dry_run_export_bundle_uses_declared_schema_contract(tmp_path):
    client = _client(tmp_path)
    bundle = client.get("/dry-run-execution/export?now_epoch=100").json()
    contract = dry_run_export_schema_contract()

    assert bundle["bundle_type"] == contract["bundle_type"]
    assert bundle["schema_version"] == contract["schema_version"]
    assert set(bundle) == set(contract["required_keys"])
    for key, expected in contract["safe_flags"].items():
        assert bundle[key] is expected

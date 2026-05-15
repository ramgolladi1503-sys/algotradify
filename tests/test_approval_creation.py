from __future__ import annotations

import json

from approval_audit import (
    ApprovalCreationRequest,
    ApprovalStatus,
    append_approval_event,
    approval_request_from_mapping,
    create_approval_event,
    validate_approval_creation,
)


def _safe_snapshot():
    return {
        "execution_permitted": False,
        "status": "BLOCKED",
        "is_order_action": False,
        "safety_visibility_only": True,
        "blockers": ["DRY_RUN_REQUIRED"],
    }


def _valid_request(**overrides):
    payload = {
        "candidate_id": "c1",
        "operator_id": "op1",
        "reason": "manual risk review completed",
        "expires_at_epoch": 200.0,
        "ts_epoch": 100.0,
        "safety_decision": _safe_snapshot(),
    }
    payload.update(overrides)
    return ApprovalCreationRequest(**payload)


def test_validate_approval_creation_requires_core_fields():
    request = ApprovalCreationRequest(
        candidate_id="",
        operator_id="",
        reason="bad",
        expires_at_epoch=0,
        ts_epoch=10,
        safety_decision={},
    )

    blockers, warnings = validate_approval_creation(request)

    assert "CANDIDATE_ID_REQUIRED" in blockers
    assert "OPERATOR_ID_REQUIRED" in blockers
    assert "APPROVAL_REASON_TOO_SHORT" in blockers
    assert "APPROVAL_EXPIRY_MUST_BE_AFTER_TIMESTAMP" in blockers
    assert "APPROVAL_EXPIRY_REQUIRED" in blockers
    assert "SAFETY_DECISION_SNAPSHOT_REQUIRED" in blockers
    assert warnings == []


def test_validate_approval_creation_rejects_unsafe_safety_snapshot():
    request = _valid_request(safety_decision={"execution_permitted": True, "status": "PERMITTED", "is_order_action": True})

    blockers, warnings = validate_approval_creation(request)

    assert "SAFETY_DECISION_ORDER_FLAG_UNSAFE" in blockers
    assert "SAFETY_DECISION_VISIBILITY_FLAG_MISSING" in warnings


def test_create_approval_event_creates_immutable_non_order_event():
    result = create_approval_event(_valid_request())

    assert result.created is True
    assert result.event is not None
    payload = result.to_dict()
    assert payload["event"]["candidate_id"] == "c1"
    assert payload["event"]["operator_id"] == "op1"
    assert payload["event"]["status"] == "APPROVED"
    assert payload["event"]["immutable_audit_event"] is True
    assert payload["event"]["is_order_action"] is False
    assert payload["is_order_action"] is False


def test_create_approval_event_does_not_create_when_invalid():
    result = create_approval_event(_valid_request(reason="bad"))

    assert result.created is False
    assert result.event is None
    assert "APPROVAL_REASON_TOO_SHORT" in result.blockers
    assert result.is_order_action is False


def test_append_approval_event_writes_jsonl(tmp_path):
    path = tmp_path / ".runtime" / "approval_audit.jsonl"

    result = append_approval_event(path, _valid_request(approval_id="approval-1234"))

    assert result.created is True
    assert result.append_path == str(path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["approval_id"] == "approval-1234"
    assert rows[0]["candidate_id"] == "c1"
    assert rows[0]["is_order_action"] is False


def test_approval_request_from_mapping_supports_rejection_alias():
    request = approval_request_from_mapping(
        {
            "candidate_id": "c1",
            "approved_by": "op1",
            "approval_reason": "manual rejection reason",
            "expiry_epoch": 200,
            "approved_at_epoch": 100,
            "approval_status": "DENIED",
            "safety_decision": _safe_snapshot(),
        }
    )

    assert request.status == ApprovalStatus.REJECTED
    assert request.operator_id == "op1"
    assert request.reason == "manual rejection reason"


def test_approval_id_is_stable_when_missing():
    first = create_approval_event(_valid_request())
    second = create_approval_event(_valid_request())

    assert first.event is not None
    assert second.event is not None
    assert first.event.approval_id == second.event.approval_id
    assert first.event.approval_id.startswith("approval-")

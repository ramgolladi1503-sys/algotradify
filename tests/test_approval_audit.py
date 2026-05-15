from __future__ import annotations

from approval_audit import ApprovalStatus, build_approval_event, normalize_approval_audit


def test_build_approval_event_is_immutable_non_order_evidence():
    event = build_approval_event(
        approval_id="a1",
        candidate_id="c1",
        operator_id="op1",
        reason="risk reviewed",
        ts_epoch=100,
        expires_at_epoch=200,
        safety_decision={"execution_permitted": False, "status": "BLOCKED"},
    )

    payload = event.to_dict(now_epoch=150)
    assert payload["approval_id"] == "a1"
    assert payload["candidate_id"] == "c1"
    assert payload["operator_id"] == "op1"
    assert payload["status"] == "APPROVED"
    assert payload["immutable_audit_event"] is True
    assert payload["is_order_action"] is False
    assert payload["safety_decision"]["status"] == "BLOCKED"


def test_approval_audit_tracks_latest_approved_status():
    summary = normalize_approval_audit(
        [
            {"approval_id": "a1", "candidate_id": "c1", "operator_id": "op1", "status": "APPROVED", "reason": "manual review", "ts_epoch": 1, "expires_at_epoch": 100},
        ],
        now_epoch=50,
    )

    assert summary.candidate_id == "c1"
    assert summary.current_status == ApprovalStatus.APPROVED
    assert summary.approval_id == "a1"
    assert summary.operator_id == "op1"
    assert summary.approved_count == 1
    assert summary.blockers == []
    assert summary.is_order_action is False


def test_approval_audit_expiry_blocks_approval():
    summary = normalize_approval_audit(
        [
            {"approval_id": "a1", "candidate_id": "c1", "operator_id": "op1", "status": "APPROVED", "reason": "expired approval", "ts_epoch": 1, "expires_at_epoch": 10},
        ],
        now_epoch=20,
    )

    assert summary.current_status == ApprovalStatus.EXPIRED
    assert summary.approved_count == 0
    assert summary.expired_count == 1
    assert summary.blockers == ["APPROVAL_EXPIRED"]
    assert summary.to_dict(now_epoch=20)["events"][0]["status"] == "EXPIRED"


def test_approval_audit_rejection_and_revocation_are_visible():
    summary = normalize_approval_audit(
        [
            {"approval_id": "a1", "candidate_id": "c1", "operator_id": "op1", "status": "APPROVED", "reason": "first approval", "ts_epoch": 1},
            {"approval_id": "a2", "candidate_id": "c1", "operator_id": "op2", "status": "REVOKED", "reason": "market changed", "ts_epoch": 2},
        ]
    )

    assert summary.current_status == ApprovalStatus.REVOKED
    assert summary.approved_count == 1
    assert summary.revoked_count == 1
    assert summary.latest_reason == "market changed"
    assert summary.blockers == ["APPROVAL_REVOKED"]


def test_approval_audit_empty_state():
    summary = normalize_approval_audit([], candidate_id="c1")

    assert summary.candidate_id == "c1"
    assert summary.current_status == ApprovalStatus.UNKNOWN
    assert summary.approval_id is None
    assert summary.events == []
    assert summary.blockers == ["NO_APPROVAL_AUDIT_EVENTS"]
    assert summary.is_order_action is False


def test_approval_audit_filters_candidate_id():
    summary = normalize_approval_audit(
        [
            {"approval_id": "a1", "candidate_id": "c1", "operator_id": "op1", "status": "APPROVED", "reason": "ok", "ts_epoch": 1},
            {"approval_id": "a2", "candidate_id": "c2", "operator_id": "op2", "status": "REJECTED", "reason": "bad", "ts_epoch": 2},
        ],
        candidate_id="c2",
    )

    assert summary.candidate_id == "c2"
    assert len(summary.events) == 1
    assert summary.current_status == ApprovalStatus.REJECTED
    assert summary.rejected_count == 1
    assert summary.blockers == ["APPROVAL_REJECTED"]


def test_approval_audit_unknown_values_are_warned():
    summary = normalize_approval_audit(
        [
            {"candidate_id": "c1", "status": "WEIRD"},
        ]
    )

    assert summary.current_status == ApprovalStatus.UNKNOWN
    assert "UNKNOWN_OPERATOR_PRESENT" in summary.warnings
    assert "UNKNOWN_APPROVAL_ID_PRESENT" in summary.warnings
    assert "UNKNOWN_APPROVAL_STATUS_PRESENT" in summary.warnings

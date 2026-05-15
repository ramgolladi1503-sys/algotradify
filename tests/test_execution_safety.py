from __future__ import annotations

from execution_safety import ExecutionMode, ExecutionSafetyPolicy, evaluate_execution_safety


def _top_executable(candidate_id="c1"):
    return {
        "status": "SELECTED",
        "selected": {
            "candidate_id": candidate_id,
            "quality_score": 90,
            "is_order": False,
        },
        "is_order": False,
    }


def _readiness(candidate_id="c1", allowed=True):
    return {
        "candidate_id": candidate_id,
        "execution_allowed": allowed,
        "status": "ALLOWED" if allowed else "BLOCKED",
    }


def test_execution_safety_blocks_by_default():
    decision = evaluate_execution_safety(ExecutionSafetyPolicy())

    assert decision.execution_permitted is False
    assert decision.status == "BLOCKED"
    assert "DRY_RUN_REQUIRED" in decision.blockers
    assert "MANUAL_APPROVAL_REQUIRED" in decision.blockers
    assert "OPERATOR_ID_REQUIRED" in decision.blockers
    assert "BROKER_CONFIRMATION_REQUIRED" in decision.blockers
    assert "NO_TOP_EXECUTABLE_SELECTED" in decision.blockers
    assert decision.requires_manual_approval is True
    assert decision.is_order_action is False


def test_execution_safety_permits_paper_mode_when_all_required_evidence_exists():
    policy = ExecutionSafetyPolicy(
        mode=ExecutionMode.PAPER,
        manual_approval_required=True,
        dry_run_required=False,
        approval_id="approval-1",
        operator_id="operator-1",
        broker_confirmation_id="broker-confirm-1",
        broker_confirmation_required=True,
        warnings_acknowledged=True,
        max_daily_loss=1000,
        current_daily_loss=100,
        max_orders_per_day=10,
        orders_today=2,
        max_quantity=100,
        requested_quantity=10,
    )

    decision = evaluate_execution_safety(policy, top_executable=_top_executable(), execution_readiness=_readiness())

    assert decision.execution_permitted is True
    assert decision.status == "PERMITTED"
    assert decision.blockers == []
    assert decision.audit["top_executable_candidate_id"] == "c1"
    assert decision.audit["execution_readiness_candidate_id"] == "c1"
    assert decision.to_dict()["is_order_action"] is False


def test_execution_safety_live_mode_still_requires_approval_and_confirmation():
    policy = ExecutionSafetyPolicy(mode=ExecutionMode.LIVE, dry_run_required=False, warnings_acknowledged=True)

    decision = evaluate_execution_safety(policy, top_executable=_top_executable(), execution_readiness=_readiness())

    assert decision.execution_permitted is False
    assert "MANUAL_APPROVAL_REQUIRED" in decision.blockers
    assert "OPERATOR_ID_REQUIRED" in decision.blockers
    assert "BROKER_CONFIRMATION_REQUIRED" in decision.blockers
    assert "LIVE_MODE_REQUIRES_STRICT_APPROVAL" in decision.warnings


def test_execution_safety_kill_switch_blocks_even_with_all_evidence():
    policy = ExecutionSafetyPolicy(
        kill_switch_enabled=True,
        dry_run_required=False,
        approval_id="approval-1",
        operator_id="operator-1",
        broker_confirmation_id="broker-confirm-1",
        warnings_acknowledged=True,
    )

    decision = evaluate_execution_safety(policy, top_executable=_top_executable(), execution_readiness=_readiness())

    assert decision.execution_permitted is False
    assert "KILL_SWITCH_ENABLED" in decision.blockers


def test_execution_safety_limits_block_when_exceeded():
    policy = ExecutionSafetyPolicy(
        dry_run_required=False,
        approval_id="approval-1",
        operator_id="operator-1",
        broker_confirmation_id="broker-confirm-1",
        warnings_acknowledged=True,
        max_daily_loss=100,
        current_daily_loss=100,
        max_orders_per_day=2,
        orders_today=2,
        max_quantity=5,
        requested_quantity=10,
    )

    decision = evaluate_execution_safety(policy, top_executable=_top_executable(), execution_readiness=_readiness())

    assert "MAX_DAILY_LOSS_REACHED" in decision.blockers
    assert "MAX_ORDERS_PER_DAY_REACHED" in decision.blockers
    assert "MAX_QUANTITY_EXCEEDED" in decision.blockers


def test_execution_safety_blocks_when_readiness_not_allowed():
    policy = ExecutionSafetyPolicy(
        dry_run_required=False,
        approval_id="approval-1",
        operator_id="operator-1",
        broker_confirmation_id="broker-confirm-1",
        warnings_acknowledged=True,
    )

    decision = evaluate_execution_safety(policy, top_executable=_top_executable(), execution_readiness=_readiness(allowed=False))

    assert decision.execution_permitted is False
    assert "EXECUTION_READINESS_NOT_ALLOWED" in decision.blockers


def test_execution_safety_blocks_unsafe_top_executable_order_flag():
    unsafe = _top_executable()
    unsafe["selected"]["is_order"] = True
    policy = ExecutionSafetyPolicy(
        dry_run_required=False,
        approval_id="approval-1",
        operator_id="operator-1",
        broker_confirmation_id="broker-confirm-1",
        warnings_acknowledged=True,
    )

    decision = evaluate_execution_safety(policy, top_executable=unsafe, execution_readiness=_readiness())

    assert decision.execution_permitted is False
    assert "TOP_EXECUTABLE_ORDER_FLAG_UNSAFE" in decision.blockers

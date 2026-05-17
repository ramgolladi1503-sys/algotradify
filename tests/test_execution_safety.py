from __future__ import annotations

import pytest

from execution_safety import (
    ExecutionMode,
    ExecutionModeContract,
    ExecutionSafetyPolicy,
    assert_broker_order_call_allowed,
    evaluate_execution_mode_contract,
    evaluate_execution_safety,
)


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


def test_execution_mode_contract_defaults_to_sim_and_blocks_broker_api():
    decision = evaluate_execution_mode_contract(ExecutionModeContract())

    assert decision.mode == ExecutionMode.SIM
    assert decision.status == "PERMITTED"
    assert decision.simulated_order_allowed is True
    assert decision.paper_order_allowed is False
    assert decision.broker_api_allowed is False
    assert decision.real_order_allowed is False
    assert decision.is_order_action is False
    assert "SIM_MODE_NO_BROKER_ORDERS" in decision.warnings


def test_sim_mode_cannot_place_broker_orders():
    with pytest.raises(PermissionError) as exc:
        assert_broker_order_call_allowed(ExecutionModeContract(mode=ExecutionMode.SIM))

    assert "mode=SIM" in str(exc.value)
    assert "SIM_MODE_NO_BROKER_ORDERS" in str(exc.value)


def test_paper_mode_cannot_call_real_broker_placement():
    decision = evaluate_execution_mode_contract(ExecutionModeContract(mode=ExecutionMode.PAPER))

    assert decision.status == "PERMITTED"
    assert decision.simulated_order_allowed is False
    assert decision.paper_order_allowed is True
    assert decision.broker_api_allowed is False
    assert decision.real_order_allowed is False
    assert "PAPER_MODE_NO_REAL_BROKER_PLACEMENT" in decision.warnings

    with pytest.raises(PermissionError) as exc:
        assert_broker_order_call_allowed(ExecutionModeContract(mode=ExecutionMode.PAPER))
    assert "mode=PAPER" in str(exc.value)


def test_live_mode_requires_broker_risk_and_kill_switch_readiness():
    decision = evaluate_execution_mode_contract(ExecutionModeContract(mode=ExecutionMode.LIVE))

    assert decision.status == "BLOCKED"
    assert decision.broker_api_allowed is False
    assert decision.real_order_allowed is False
    assert "LIVE_REAL_BROKER_ADAPTER_NOT_ENABLED" in decision.blockers
    assert "LIVE_BROKER_READINESS_REQUIRED" in decision.blockers
    assert "LIVE_RISK_READINESS_REQUIRED" in decision.blockers
    assert "LIVE_KILL_SWITCH_READINESS_REQUIRED" in decision.blockers
    assert "LIVE_MODE_REQUIRES_STRICT_APPROVAL" in decision.warnings


def test_live_mode_allows_broker_guard_only_when_all_live_flags_exist():
    contract = ExecutionModeContract(
        mode=ExecutionMode.LIVE,
        real_broker_order_adapter_enabled=True,
        live_broker_ready=True,
        live_risk_ready=True,
        live_kill_switch_ready=True,
    )

    decision = evaluate_execution_mode_contract(contract)

    assert decision.status == "PERMITTED"
    assert decision.broker_api_allowed is True
    assert decision.real_order_allowed is True
    assert decision.simulated_order_allowed is False
    assert decision.paper_order_allowed is False
    assert_broker_order_call_allowed(contract)


def test_execution_safety_blocks_by_default():
    decision = evaluate_execution_safety(ExecutionSafetyPolicy())

    assert decision.mode == ExecutionMode.SIM
    assert decision.execution_permitted is False
    assert decision.status == "BLOCKED"
    assert "DRY_RUN_REQUIRED" in decision.blockers
    assert "MANUAL_APPROVAL_REQUIRED" in decision.blockers
    assert "OPERATOR_ID_REQUIRED" in decision.blockers
    assert "BROKER_CONFIRMATION_REQUIRED" in decision.blockers
    assert "NO_TOP_EXECUTABLE_SELECTED" in decision.blockers
    assert decision.requires_manual_approval is True
    assert decision.is_order_action is False
    assert decision.broker_api_allowed is False
    assert decision.real_order_allowed is False
    assert decision.audit["execution_mode_contract"]["mode"] == "SIM"
    assert decision.audit["execution_mode_decision"]["broker_api_allowed"] is False


def test_execution_safety_permits_sim_mode_when_all_required_evidence_exists_without_broker_api():
    policy = ExecutionSafetyPolicy(
        mode=ExecutionMode.SIM,
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
    assert decision.simulated_order_allowed is True
    assert decision.paper_order_allowed is False
    assert decision.broker_api_allowed is False
    assert decision.real_order_allowed is False
    assert decision.audit["top_executable_candidate_id"] == "c1"
    assert decision.audit["execution_readiness_candidate_id"] == "c1"
    assert decision.to_dict()["is_order_action"] is False


def test_execution_safety_permits_paper_mode_when_all_required_evidence_exists_without_real_broker():
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
    assert decision.simulated_order_allowed is False
    assert decision.paper_order_allowed is True
    assert decision.broker_api_allowed is False
    assert decision.real_order_allowed is False
    assert decision.audit["top_executable_candidate_id"] == "c1"
    assert decision.audit["execution_readiness_candidate_id"] == "c1"
    assert decision.to_dict()["is_order_action"] is False


def test_execution_safety_live_mode_requires_explicit_live_readiness_flags():
    policy = ExecutionSafetyPolicy(
        mode=ExecutionMode.LIVE,
        dry_run_required=False,
        approval_id="approval-1",
        operator_id="operator-1",
        broker_confirmation_id="broker-confirm-1",
        warnings_acknowledged=True,
    )

    decision = evaluate_execution_safety(policy, top_executable=_top_executable(), execution_readiness=_readiness())

    assert decision.execution_permitted is False
    assert "LIVE_REAL_BROKER_ADAPTER_NOT_ENABLED" in decision.blockers
    assert "LIVE_BROKER_READINESS_REQUIRED" in decision.blockers
    assert "LIVE_RISK_READINESS_REQUIRED" in decision.blockers
    assert "LIVE_KILL_SWITCH_READINESS_REQUIRED" in decision.blockers
    assert "LIVE_MODE_REQUIRES_STRICT_APPROVAL" in decision.warnings
    assert decision.broker_api_allowed is False
    assert decision.real_order_allowed is False


def test_execution_safety_live_mode_requires_approval_and_confirmation_too():
    policy = ExecutionSafetyPolicy(
        mode=ExecutionMode.LIVE,
        dry_run_required=False,
        warnings_acknowledged=True,
        live_broker_ready=True,
        live_risk_ready=True,
        live_kill_switch_ready=True,
        real_broker_order_adapter_enabled=True,
    )

    decision = evaluate_execution_safety(policy, top_executable=_top_executable(), execution_readiness=_readiness())

    assert decision.execution_permitted is False
    assert "MANUAL_APPROVAL_REQUIRED" in decision.blockers
    assert "OPERATOR_ID_REQUIRED" in decision.blockers
    assert "BROKER_CONFIRMATION_REQUIRED" in decision.blockers
    assert "LIVE_MODE_REQUIRES_STRICT_APPROVAL" in decision.warnings


def test_execution_safety_live_mode_permits_only_when_all_safety_and_live_flags_pass():
    policy = ExecutionSafetyPolicy(
        mode=ExecutionMode.LIVE,
        dry_run_required=False,
        approval_id="approval-1",
        operator_id="operator-1",
        broker_confirmation_id="broker-confirm-1",
        warnings_acknowledged=True,
        live_broker_ready=True,
        live_risk_ready=True,
        live_kill_switch_ready=True,
        real_broker_order_adapter_enabled=True,
    )

    decision = evaluate_execution_safety(policy, top_executable=_top_executable(), execution_readiness=_readiness())

    assert decision.execution_permitted is True
    assert decision.status == "PERMITTED"
    assert decision.blockers == []
    assert decision.broker_api_allowed is True
    assert decision.real_order_allowed is True


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
    assert decision.broker_api_allowed is False
    assert decision.real_order_allowed is False


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

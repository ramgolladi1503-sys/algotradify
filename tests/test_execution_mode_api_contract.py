from __future__ import annotations

from execution_safety import ExecutionMode
from api.execution_mode_policy import (
    execution_safety_policy_from_query,
    parse_execution_mode_from_query,
)


def test_execution_mode_api_defaults_missing_mode_to_sim():
    parsed = parse_execution_mode_from_query({})

    assert parsed.mode == ExecutionMode.SIM
    assert parsed.raw_mode is None
    assert parsed.invalid_mode is False
    assert parsed.blockers == []
    assert "EXECUTION_MODE_DEFAULTED_TO_SIM" in parsed.warnings
    assert parsed.to_dict()["is_order_action"] is False


def test_execution_mode_api_accepts_only_exact_supported_modes_case_insensitive():
    for raw, expected in [("sim", ExecutionMode.SIM), ("PAPER", ExecutionMode.PAPER), ("live", ExecutionMode.LIVE)]:
        parsed = parse_execution_mode_from_query({"mode": raw})
        assert parsed.mode == expected
        assert parsed.invalid_mode is False
        assert parsed.blockers == []
        assert parsed.warnings == []


def test_execution_mode_api_rejects_unknown_mode_instead_of_falling_back_to_paper():
    parsed = parse_execution_mode_from_query({"mode": "production"})

    assert parsed.mode == ExecutionMode.SIM
    assert parsed.raw_mode == "production"
    assert parsed.invalid_mode is True
    assert "INVALID_EXECUTION_MODE" in parsed.blockers
    assert "EXECUTION_MODE_FORCED_TO_SIM" in parsed.warnings
    assert "PAPER" in parsed.to_dict()["supported_modes"]


def test_execution_safety_policy_from_query_uses_sim_default_and_preserves_invalid_mode_metadata():
    policy, parsed = execution_safety_policy_from_query({"mode": "REAL", "dry_run_required": "false"})

    assert policy.mode == ExecutionMode.SIM
    assert policy.dry_run_required is False
    assert parsed.invalid_mode is True
    assert "INVALID_EXECUTION_MODE" in parsed.blockers


def test_execution_safety_policy_from_query_maps_live_readiness_flags_explicitly():
    policy, parsed = execution_safety_policy_from_query(
        {
            "mode": "LIVE",
            "live_broker_ready": "true",
            "live_risk_ready": "true",
            "live_kill_switch_ready": "true",
            "real_broker_order_adapter_enabled": "true",
            "approval_id": "a1",
            "operator_id": "o1",
            "broker_confirmation_id": "b1",
            "warnings_acknowledged": "true",
            "dry_run_required": "false",
        }
    )

    assert parsed.mode == ExecutionMode.LIVE
    assert parsed.blockers == []
    assert policy.mode == ExecutionMode.LIVE
    assert policy.live_broker_ready is True
    assert policy.live_risk_ready is True
    assert policy.live_kill_switch_ready is True
    assert policy.real_broker_order_adapter_enabled is True
    assert policy.approval_id == "a1"
    assert policy.operator_id == "o1"
    assert policy.broker_confirmation_id == "b1"
    assert policy.warnings_acknowledged is True
    assert policy.dry_run_required is False


def test_execution_safety_policy_from_query_never_implicitly_enables_live_flags():
    policy, parsed = execution_safety_policy_from_query({"mode": "LIVE"})

    assert parsed.mode == ExecutionMode.LIVE
    assert policy.mode == ExecutionMode.LIVE
    assert policy.live_broker_ready is False
    assert policy.live_risk_ready is False
    assert policy.live_kill_switch_ready is False
    assert policy.real_broker_order_adapter_enabled is False

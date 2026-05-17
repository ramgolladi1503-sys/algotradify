from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from execution_safety import ExecutionMode, ExecutionSafetyPolicy


SUPPORTED_EXECUTION_MODE_VALUES = tuple(mode.value for mode in ExecutionMode)


@dataclass(frozen=True)
class ExecutionModeApiParseResult:
    mode: ExecutionMode
    raw_mode: str | None
    invalid_mode: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "raw_mode": self.raw_mode,
            "invalid_mode": self.invalid_mode,
            "supported_modes": list(SUPPORTED_EXECUTION_MODE_VALUES),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "is_order_action": self.is_order_action,
        }


def parse_execution_mode_from_query(query_params: Mapping[str, Any]) -> ExecutionModeApiParseResult:
    raw = query_params.get("mode")
    if raw is None or str(raw).strip() == "":
        return ExecutionModeApiParseResult(
            mode=ExecutionMode.SIM,
            raw_mode=None,
            warnings=["EXECUTION_MODE_DEFAULTED_TO_SIM"],
        )

    normalized = str(raw).strip().upper()
    if normalized in SUPPORTED_EXECUTION_MODE_VALUES:
        return ExecutionModeApiParseResult(mode=ExecutionMode(normalized), raw_mode=str(raw))

    return ExecutionModeApiParseResult(
        mode=ExecutionMode.SIM,
        raw_mode=str(raw),
        invalid_mode=True,
        blockers=["INVALID_EXECUTION_MODE"],
        warnings=["EXECUTION_MODE_FORCED_TO_SIM"],
    )


def bool_from_query(query_params: Mapping[str, Any], name: str, default: bool) -> bool:
    raw = query_params.get(name)
    if raw is None:
        return default
    return str(raw).lower() in {"1", "true", "yes", "y", "on"}


def float_from_query(query_params: Mapping[str, Any], name: str, default: float) -> float:
    try:
        return float(query_params.get(name, default))
    except (TypeError, ValueError):
        return default


def int_from_query(query_params: Mapping[str, Any], name: str, default: int) -> int:
    try:
        return int(query_params.get(name, default))
    except (TypeError, ValueError):
        return default


def execution_safety_policy_from_query(query_params: Mapping[str, Any]) -> tuple[ExecutionSafetyPolicy, ExecutionModeApiParseResult]:
    parsed_mode = parse_execution_mode_from_query(query_params)
    policy = ExecutionSafetyPolicy(
        mode=parsed_mode.mode,
        manual_approval_required=bool_from_query(query_params, "manual_approval_required", True),
        kill_switch_enabled=bool_from_query(query_params, "kill_switch_enabled", False),
        broker_confirmation_required=bool_from_query(query_params, "broker_confirmation_required", True),
        dry_run_required=bool_from_query(query_params, "dry_run_required", True),
        max_daily_loss=float_from_query(query_params, "max_daily_loss", 0.0),
        current_daily_loss=float_from_query(query_params, "current_daily_loss", 0.0),
        max_orders_per_day=int_from_query(query_params, "max_orders_per_day", 0),
        orders_today=int_from_query(query_params, "orders_today", 0),
        max_quantity=int_from_query(query_params, "max_quantity", 0),
        requested_quantity=int_from_query(query_params, "requested_quantity", 0),
        approval_id=query_params.get("approval_id"),
        operator_id=query_params.get("operator_id"),
        broker_confirmation_id=query_params.get("broker_confirmation_id"),
        warnings_acknowledged=bool_from_query(query_params, "warnings_acknowledged", False),
        live_broker_ready=bool_from_query(query_params, "live_broker_ready", False),
        live_risk_ready=bool_from_query(query_params, "live_risk_ready", False),
        live_kill_switch_ready=bool_from_query(query_params, "live_kill_switch_ready", False),
        real_broker_order_adapter_enabled=bool_from_query(query_params, "real_broker_order_adapter_enabled", False),
    )
    return policy, parsed_mode

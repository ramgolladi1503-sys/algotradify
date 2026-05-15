from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ExecutionMode(StrEnum):
    PAPER = "PAPER"
    LIVE = "LIVE"


@dataclass(frozen=True)
class ExecutionSafetyPolicy:
    mode: ExecutionMode = ExecutionMode.PAPER
    manual_approval_required: bool = True
    kill_switch_enabled: bool = False
    broker_confirmation_required: bool = True
    dry_run_required: bool = True
    max_daily_loss: float = 0.0
    current_daily_loss: float = 0.0
    max_orders_per_day: int = 0
    orders_today: int = 0
    max_quantity: int = 0
    requested_quantity: int = 0
    approval_id: str | None = None
    operator_id: str | None = None
    broker_confirmation_id: str | None = None
    warnings_acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "manual_approval_required": self.manual_approval_required,
            "kill_switch_enabled": self.kill_switch_enabled,
            "broker_confirmation_required": self.broker_confirmation_required,
            "dry_run_required": self.dry_run_required,
            "max_daily_loss": self.max_daily_loss,
            "current_daily_loss": self.current_daily_loss,
            "max_orders_per_day": self.max_orders_per_day,
            "orders_today": self.orders_today,
            "max_quantity": self.max_quantity,
            "requested_quantity": self.requested_quantity,
            "approval_id": self.approval_id,
            "operator_id": self.operator_id,
            "broker_confirmation_id": self.broker_confirmation_id,
            "warnings_acknowledged": self.warnings_acknowledged,
        }


@dataclass(frozen=True)
class ExecutionSafetyDecision:
    execution_permitted: bool
    mode: ExecutionMode
    status: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)

    @property
    def is_order_action(self) -> bool:
        return False

    @property
    def requires_manual_approval(self) -> bool:
        return "MANUAL_APPROVAL_REQUIRED" in self.blockers

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_permitted": self.execution_permitted,
            "mode": self.mode.value,
            "status": self.status,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "audit": dict(self.audit),
            "requires_manual_approval": self.requires_manual_approval,
            "is_order_action": self.is_order_action,
        }


def evaluate_execution_safety(
    policy: ExecutionSafetyPolicy,
    *,
    top_executable: dict[str, Any] | None = None,
    execution_readiness: dict[str, Any] | None = None,
) -> ExecutionSafetyDecision:
    blockers: list[str] = []
    warnings: list[str] = []

    if policy.kill_switch_enabled:
        blockers.append("KILL_SWITCH_ENABLED")

    if policy.mode == ExecutionMode.LIVE:
        warnings.append("LIVE_MODE_REQUIRES_STRICT_APPROVAL")
    else:
        warnings.append("PAPER_MODE_ONLY")

    if policy.dry_run_required:
        blockers.append("DRY_RUN_REQUIRED")

    if policy.manual_approval_required and not policy.approval_id:
        blockers.append("MANUAL_APPROVAL_REQUIRED")

    if policy.manual_approval_required and not policy.operator_id:
        blockers.append("OPERATOR_ID_REQUIRED")

    if policy.broker_confirmation_required and not policy.broker_confirmation_id:
        blockers.append("BROKER_CONFIRMATION_REQUIRED")

    if policy.max_daily_loss > 0 and policy.current_daily_loss >= policy.max_daily_loss:
        blockers.append("MAX_DAILY_LOSS_REACHED")

    if policy.max_orders_per_day > 0 and policy.orders_today >= policy.max_orders_per_day:
        blockers.append("MAX_ORDERS_PER_DAY_REACHED")

    if policy.max_quantity > 0 and policy.requested_quantity > policy.max_quantity:
        blockers.append("MAX_QUANTITY_EXCEEDED")

    if top_executable is None or top_executable.get("status") != "SELECTED" or not top_executable.get("selected"):
        blockers.append("NO_TOP_EXECUTABLE_SELECTED")

    selected = top_executable.get("selected") if isinstance(top_executable, dict) else None
    if isinstance(selected, dict) and selected.get("is_order") is not False:
        blockers.append("TOP_EXECUTABLE_ORDER_FLAG_UNSAFE")

    if execution_readiness is not None and not execution_readiness.get("execution_allowed"):
        blockers.append("EXECUTION_READINESS_NOT_ALLOWED")

    if not policy.warnings_acknowledged:
        warnings.append("WARNINGS_NOT_ACKNOWLEDGED")

    blockers = _dedupe(blockers)
    warnings = _dedupe(warnings)
    permitted = not blockers and policy.mode in {ExecutionMode.PAPER, ExecutionMode.LIVE}

    return ExecutionSafetyDecision(
        execution_permitted=permitted,
        mode=policy.mode,
        status="PERMITTED" if permitted else "BLOCKED",
        blockers=blockers,
        warnings=warnings,
        audit={
            "policy": policy.to_dict(),
            "top_executable_candidate_id": _candidate_id(top_executable),
            "execution_readiness_candidate_id": execution_readiness.get("candidate_id") if isinstance(execution_readiness, dict) else None,
            "safety_contract_version": "v1",
        },
    )


def _candidate_id(top_executable: dict[str, Any] | None) -> str | None:
    selected = top_executable.get("selected") if isinstance(top_executable, dict) else None
    if isinstance(selected, dict):
        return selected.get("candidate_id")
    return None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agent_system.handoff_contract import agent_handoff_schema_contract
from agent_system.handoff_validator import validate_handoff_evidence
from agent_system.role_registry import SAFE_ROLE_FLAGS, validate_agent_role_registry
from agent_system.workflow_state import validate_agent_workflow_state_machine
from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION


AGENT_ARCHITECTURE_GATE_CONTRACT = "agent_architecture_ci_gate_v1"

TASK_ID_PATTERNS = (
    re.compile(r"\bAGENT[-_ ]PR[-_ ]?(\d+)\b", re.IGNORECASE),
    re.compile(r"\bAgent\s+PR\s+(\d+)\b", re.IGNORECASE),
)

REQUIRED_GATE_SAFE_FLAGS = {
    **SAFE_ROLE_FLAGS,
    "allowed_for_runtime_wiring": False,
    "allowed_for_broker_api": False,
}


@dataclass(frozen=True)
class AgentArchitectureGateReport:
    schema_version: int
    contract: str
    task_id: str
    valid: bool
    blockers: tuple[str, ...]
    role_registry_valid: bool
    workflow_state_valid: bool
    handoff_contract_present: bool
    handoff_evidence_valid: bool
    handoff_roles_found: tuple[str, ...]
    handoff_missing_roles: tuple[str, ...]
    read_only: bool
    is_order_action: bool
    broker_api_called: bool
    live_mode_touched: bool
    allowed_for_live_execution: bool
    real_order_id: None
    allowed_for_runtime_wiring: bool
    allowed_for_broker_api: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        payload["handoff_roles_found"] = list(self.handoff_roles_found)
        payload["handoff_missing_roles"] = list(self.handoff_missing_roles)
        payload["metadata"] = dict(self.metadata)
        return payload


def _contains_path_traversal(value: str) -> bool:
    return "\\" in value or value.startswith("/") or ".." in value.replace("\\", "/").split("/")


def resolve_agent_task_id(task_ref: str) -> str:
    value = task_ref.strip()
    if not value:
        raise ValueError("TASK_REF_MISSING")
    if _contains_path_traversal(value):
        raise ValueError("TASK_REF_UNSAFE")
    if re.fullmatch(r"AGENT-PR\d+", value, flags=re.IGNORECASE):
        number = re.search(r"\d+", value)
        if not number:
            raise ValueError("TASK_REF_MISSING_NUMBER")
        return f"AGENT-PR{number.group(0)}"
    for pattern in TASK_ID_PATTERNS:
        match = pattern.search(value)
        if match:
            return f"AGENT-PR{match.group(1)}"
    raise ValueError("TASK_REF_CANNOT_RESOLVE_AGENT_TASK_ID")


def run_agent_architecture_gate(*, task_ref: str, handoff_dir: str | Path = "docs/pr-handoffs") -> AgentArchitectureGateReport:
    """Run the PR 15 architecture gate.

    This gate validates governance contracts and handoff evidence only. It does not audit
    changed files, inspect PR templates, generate architecture replay reports, call broker
    APIs, or mutate runtime state.
    """

    task_id = resolve_agent_task_id(task_ref)
    blockers: list[str] = []

    role_registry = validate_agent_role_registry()
    if not role_registry.get("valid"):
        blockers.append("ROLE_REGISTRY_INVALID")

    workflow_state = validate_agent_workflow_state_machine()
    if not workflow_state.get("valid"):
        blockers.append("WORKFLOW_STATE_MACHINE_INVALID")

    handoff_contract = agent_handoff_schema_contract()
    handoff_contract_present = handoff_contract.get("contract") == "agent_role_handoff_artifact_v1"
    if not handoff_contract_present:
        blockers.append("HANDOFF_CONTRACT_INVALID")

    handoff_report = validate_handoff_evidence(task_id=task_id, handoff_dir=handoff_dir)
    if not handoff_report.valid:
        blockers.extend(f"HANDOFF_EVIDENCE:{blocker}" for blocker in handoff_report.blockers)

    return AgentArchitectureGateReport(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        contract=AGENT_ARCHITECTURE_GATE_CONTRACT,
        task_id=task_id,
        valid=not blockers,
        blockers=tuple(sorted(set(blockers))),
        role_registry_valid=bool(role_registry.get("valid")),
        workflow_state_valid=bool(workflow_state.get("valid")),
        handoff_contract_present=handoff_contract_present,
        handoff_evidence_valid=handoff_report.valid,
        handoff_roles_found=handoff_report.roles_found,
        handoff_missing_roles=handoff_report.missing_roles,
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        metadata={
            "scope": "ci_architecture_gate_only_no_changed_file_audit_no_pr_template_no_execution",
            "handoff_dir": str(handoff_dir),
            "handoff_blockers": list(handoff_report.blockers),
        },
        **SAFE_ROLE_FLAGS,
    )


def agent_architecture_gate_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": AGENT_ARCHITECTURE_GATE_CONTRACT,
        "required_checks": [
            "role_registry_valid",
            "workflow_state_valid",
            "handoff_contract_present",
            "handoff_evidence_valid",
        ],
        "required_safe_flags": dict(REQUIRED_GATE_SAFE_FLAGS),
        "scope": "ci_architecture_gate_only_no_changed_file_audit_no_pr_template_no_execution",
    }

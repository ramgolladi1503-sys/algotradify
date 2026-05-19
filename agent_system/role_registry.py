from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION, AgentAction, AgentSource


AGENT_ROLE_REGISTRY_CONTRACT = "agent_role_registry_v1"


class AgentRole(str, Enum):
    """Role-based mini-agent architecture roles.

    These roles are governance contracts, not personalities. They define what a role may
    do, what it must never do, and what proof it must produce.
    """

    SCOPE_OWNER = "scope_owner"
    GRILL_REVIEWER = "grill_reviewer"
    HERMES_ARCHITECT = "hermes_architect"
    GSD_IMPLEMENTER = "gsd_implementer"
    QA_SAFETY_REVIEWER = "qa_safety_reviewer"
    EVIDENCE_RECORDER = "evidence_recorder"
    HUMAN_APPROVER = "human_approver"


FORBIDDEN_ROLE_ACTIONS = frozenset(
    {
        AgentAction.PLACE_ORDER.value,
        AgentAction.MODIFY_ORDER.value,
        AgentAction.CANCEL_ORDER.value,
        AgentAction.EXIT_POSITION.value,
        AgentAction.ENABLE_LIVE.value,
        AgentAction.DISABLE_RISK_GATE.value,
        AgentAction.CHANGE_BROKER_CONFIG.value,
        AgentAction.CHANGE_LIVE_CONFIG.value,
        AgentAction.CALL_BROKER_API.value,
    }
)

FORBIDDEN_ROLE_PATH_PREFIXES = (
    ".env",
    "credentials.py",
    "config/secrets",
    "runtime/live",
    "logs/broker",
    "broker_contract/",
    "execution_safety/live",
    "execution_readiness/live",
    "paper_broker/live",
)

HIGH_RISK_ROLE_PATH_PREFIXES = (
    "agent_system/",
    "api/",
    "config/",
    "core/",
    "execution_readiness/",
    "execution_safety/",
    "main.py",
    "paper_trading/",
    "run_live.sh",
    "runtime_contract.py",
)

SAFE_ROLE_FLAGS = {
    "read_only": True,
    "is_order_action": False,
    "broker_api_called": False,
    "live_mode_touched": False,
    "allowed_for_live_execution": False,
    "real_order_id": None,
}


@dataclass(frozen=True)
class AgentRoleContract:
    schema_version: int
    role_id: str
    display_name: str
    purpose: str
    source_agents: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    allowed_path_prefixes: tuple[str, ...]
    forbidden_path_prefixes: tuple[str, ...]
    required_outputs: tuple[str, ...]
    handoff_targets: tuple[str, ...]
    requires_human_approval_for_high_risk: bool
    may_generate_patch: bool
    may_modify_implementation: bool
    may_review_safety: bool
    may_record_evidence: bool
    may_approve_merge: bool
    allowed_for_runtime_wiring: bool
    allowed_for_broker_api: bool
    allowed_for_live_execution: bool
    read_only: bool
    is_order_action: bool
    broker_api_called: bool
    live_mode_touched: bool
    real_order_id: None
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "source_agents",
            "allowed_actions",
            "forbidden_actions",
            "allowed_path_prefixes",
            "forbidden_path_prefixes",
            "required_outputs",
            "handoff_targets",
        ):
            payload[key] = list(getattr(self, key))
        payload["metadata"] = dict(self.metadata)
        return payload


def _contract(
    *,
    role_id: AgentRole,
    display_name: str,
    purpose: str,
    source_agents: tuple[str, ...],
    allowed_actions: tuple[str, ...],
    allowed_path_prefixes: tuple[str, ...],
    required_outputs: tuple[str, ...],
    handoff_targets: tuple[str, ...],
    requires_human_approval_for_high_risk: bool = True,
    may_generate_patch: bool = False,
    may_modify_implementation: bool = False,
    may_review_safety: bool = False,
    may_record_evidence: bool = False,
    may_approve_merge: bool = False,
) -> AgentRoleContract:
    return AgentRoleContract(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        role_id=role_id.value,
        display_name=display_name,
        purpose=purpose,
        source_agents=tuple(sorted(source_agents)),
        allowed_actions=tuple(sorted(allowed_actions)),
        forbidden_actions=tuple(sorted(FORBIDDEN_ROLE_ACTIONS)),
        allowed_path_prefixes=tuple(allowed_path_prefixes),
        forbidden_path_prefixes=FORBIDDEN_ROLE_PATH_PREFIXES,
        required_outputs=tuple(required_outputs),
        handoff_targets=tuple(handoff_targets),
        requires_human_approval_for_high_risk=requires_human_approval_for_high_risk,
        may_generate_patch=may_generate_patch,
        may_modify_implementation=may_modify_implementation,
        may_review_safety=may_review_safety,
        may_record_evidence=may_record_evidence,
        may_approve_merge=may_approve_merge,
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        allowed_for_live_execution=False,
        read_only=True,
        is_order_action=False,
        broker_api_called=False,
        live_mode_touched=False,
        real_order_id=None,
        metadata={
            "contract": AGENT_ROLE_REGISTRY_CONTRACT,
            "scope": "role_registry_only_no_workflow_no_ci_no_execution",
        },
    )


def build_agent_role_registry() -> dict[str, AgentRoleContract]:
    """Return the locked PR 11 role registry.

    This registry is pure contract data. It does not run agents, approve patches,
    validate workflow state, inspect git diffs, or call broker/runtime code.
    """

    return {
        AgentRole.SCOPE_OWNER.value: _contract(
            role_id=AgentRole.SCOPE_OWNER,
            display_name="Scope Owner",
            purpose="Own task boundary, files allowed, files forbidden, and non-goals before design or implementation.",
            source_agents=(AgentSource.MANUAL.value,),
            allowed_actions=(
                AgentAction.CRITIQUE_SCOPE.value,
                AgentAction.FIND_FAKE_PROGRESS.value,
                AgentAction.PLAN_PR.value,
                AgentAction.CREATE_ACCEPTANCE_GATES.value,
            ),
            allowed_path_prefixes=("docs/", "tests/", "agent_system/"),
            required_outputs=(
                "task_boundary",
                "files_allowed",
                "files_forbidden",
                "non_goals",
                "reject_conditions",
            ),
            handoff_targets=(AgentRole.GRILL_REVIEWER.value, AgentRole.HERMES_ARCHITECT.value),
        ),
        AgentRole.GRILL_REVIEWER.value: _contract(
            role_id=AgentRole.GRILL_REVIEWER,
            display_name="Grill Reviewer",
            purpose="Challenge scope, weak assumptions, fake progress, overengineering, and missing proof.",
            source_agents=(AgentSource.GRILL_ME.value,),
            allowed_actions=(
                AgentAction.CRITIQUE_SCOPE.value,
                AgentAction.REVIEW_PR.value,
                AgentAction.AUDIT_RISK.value,
                AgentAction.FIND_FAKE_PROGRESS.value,
            ),
            allowed_path_prefixes=("docs/", "tests/"),
            required_outputs=(
                "risks_found",
                "fake_progress_checks",
                "scope_drift_checks",
                "reject_conditions",
            ),
            handoff_targets=(AgentRole.HERMES_ARCHITECT.value, AgentRole.QA_SAFETY_REVIEWER.value),
        ),
        AgentRole.HERMES_ARCHITECT.value: _contract(
            role_id=AgentRole.HERMES_ARCHITECT,
            display_name="Hermes Architect",
            purpose="Define architecture, contracts, allowed files, non-goals, and acceptance gates.",
            source_agents=(AgentSource.HERMES.value,),
            allowed_actions=(
                AgentAction.DESIGN_ARCHITECTURE.value,
                AgentAction.DEFINE_CONTRACT.value,
                AgentAction.MAP_WORKFLOW.value,
                AgentAction.CREATE_ACCEPTANCE_GATES.value,
                AgentAction.UPDATE_DOCS.value,
            ),
            allowed_path_prefixes=("docs/", "tests/", "agent_system/"),
            required_outputs=(
                "architecture_decision",
                "contract_boundaries",
                "files_to_change",
                "files_not_to_touch",
                "acceptance_gates",
            ),
            handoff_targets=(AgentRole.GSD_IMPLEMENTER.value, AgentRole.QA_SAFETY_REVIEWER.value),
        ),
        AgentRole.GSD_IMPLEMENTER.value: _contract(
            role_id=AgentRole.GSD_IMPLEMENTER,
            display_name="GSD Implementer",
            purpose="Implement only the approved scoped patch and behavior tests.",
            source_agents=(AgentSource.GSD.value,),
            allowed_actions=(
                AgentAction.PLAN_PR.value,
                AgentAction.GENERATE_TESTS.value,
                AgentAction.GENERATE_PATCH.value,
                AgentAction.FIX_TEST_FAILURE.value,
                AgentAction.UPDATE_DOCS.value,
            ),
            allowed_path_prefixes=("agent_system/", "docs/", "tests/"),
            required_outputs=(
                "patch_summary",
                "changed_files",
                "tests_added",
                "test_commands",
                "implementation_boundary",
            ),
            handoff_targets=(AgentRole.QA_SAFETY_REVIEWER.value, AgentRole.EVIDENCE_RECORDER.value),
            may_generate_patch=True,
            may_modify_implementation=True,
        ),
        AgentRole.QA_SAFETY_REVIEWER.value: _contract(
            role_id=AgentRole.QA_SAFETY_REVIEWER,
            display_name="QA/Safety Reviewer",
            purpose="Review behavior tests, changed-file scope, safety flags, and broker/live/order boundaries.",
            source_agents=(AgentSource.MANUAL.value, AgentSource.GRILL_ME.value),
            allowed_actions=(
                AgentAction.REVIEW_PR.value,
                AgentAction.AUDIT_RISK.value,
                AgentAction.FIND_FAKE_PROGRESS.value,
            ),
            allowed_path_prefixes=("docs/", "tests/"),
            required_outputs=(
                "test_strength_review",
                "safety_boundary_review",
                "changed_file_review",
                "broker_live_order_boundary_review",
            ),
            handoff_targets=(AgentRole.EVIDENCE_RECORDER.value, AgentRole.HUMAN_APPROVER.value),
            may_review_safety=True,
        ),
        AgentRole.EVIDENCE_RECORDER.value: _contract(
            role_id=AgentRole.EVIDENCE_RECORDER,
            display_name="Evidence Recorder",
            purpose="Record commands, test results, acceptance proof, safety boundary, and reject conditions.",
            source_agents=(AgentSource.MANUAL.value,),
            allowed_actions=(
                AgentAction.REVIEW_PR.value,
                AgentAction.UPDATE_DOCS.value,
            ),
            allowed_path_prefixes=("docs/", "tests/"),
            required_outputs=(
                "commands_run",
                "test_results",
                "acceptance_proof",
                "safety_boundary",
                "reject_conditions",
            ),
            handoff_targets=(AgentRole.HUMAN_APPROVER.value,),
            may_record_evidence=True,
        ),
        AgentRole.HUMAN_APPROVER.value: _contract(
            role_id=AgentRole.HUMAN_APPROVER,
            display_name="Human Approver",
            purpose="Decide merge-readiness only after all role evidence and safety gates pass.",
            source_agents=(AgentSource.MANUAL.value,),
            allowed_actions=(
                AgentAction.REVIEW_PR.value,
                AgentAction.AUDIT_RISK.value,
            ),
            allowed_path_prefixes=("docs/", "tests/"),
            required_outputs=(
                "merge_readiness_decision",
                "approval_reason",
                "known_risks",
            ),
            handoff_targets=(),
            may_review_safety=True,
            may_approve_merge=True,
        ),
    }


def get_agent_role_contract(role_id: str) -> AgentRoleContract:
    registry = build_agent_role_registry()
    normalized = role_id.strip().lower().replace("-", "_").replace(" ", "_")
    try:
        return registry[normalized]
    except KeyError as exc:
        raise KeyError(f"UNKNOWN_AGENT_ROLE:{role_id}") from exc


def _starts_with_any(path: str, prefixes: Sequence[str]) -> bool:
    normalized = path.strip().replace("\\", "/")
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in prefixes)


def assess_role_request(
    *,
    role_id: str,
    source_agent: str,
    action: str,
    requested_paths: Sequence[str],
    human_approved: bool = False,
) -> dict[str, Any]:
    """Assess a role/action/path request against the PR 11 role registry.

    This is not the PR 12 workflow state machine. It only answers whether the role
    contract allows the requested source, action, and paths.
    """

    role = get_agent_role_contract(role_id)
    normalized_source = source_agent.strip().lower().replace("-", "_").replace(" ", "_")
    normalized_action = action.strip().upper().replace("-", "_").replace(" ", "_")
    blockers: list[str] = []
    warnings: list[str] = []

    if normalized_source not in role.source_agents:
        blockers.append("SOURCE_AGENT_NOT_ALLOWED_FOR_ROLE")

    if normalized_action not in role.allowed_actions:
        blockers.append("ACTION_NOT_ALLOWED_FOR_ROLE")

    if normalized_action in role.forbidden_actions:
        blockers.append("FORBIDDEN_ACTION_FOR_ROLE")

    clean_paths = tuple(path.strip().replace("\\", "/") for path in requested_paths if str(path).strip())
    if not clean_paths:
        blockers.append("REQUESTED_PATHS_MISSING")

    for path in clean_paths:
        if _starts_with_any(path, role.forbidden_path_prefixes):
            blockers.append("FORBIDDEN_PATH_FOR_ROLE")
        if role.allowed_path_prefixes and not _starts_with_any(path, role.allowed_path_prefixes):
            blockers.append("PATH_OUTSIDE_ROLE_ALLOWED_PREFIXES")
        if _starts_with_any(path, HIGH_RISK_ROLE_PATH_PREFIXES) and role.requires_human_approval_for_high_risk and not human_approved:
            warnings.append("HIGH_RISK_PATH_REQUIRES_HUMAN_APPROVAL")

    accepted = not blockers and not warnings

    return {
        "contract": AGENT_ROLE_REGISTRY_CONTRACT,
        "role_id": role.role_id,
        "accepted": accepted,
        "state": "ROLE_REQUEST_ALLOWED" if accepted else "ROLE_REQUEST_BLOCKED",
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "allowed_for_runtime_wiring": False,
        "allowed_for_broker_api": False,
        "allowed_for_live_execution": False,
        **SAFE_ROLE_FLAGS,
    }


def agent_role_registry_schema_contract() -> dict[str, Any]:
    registry = build_agent_role_registry()
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": AGENT_ROLE_REGISTRY_CONTRACT,
        "roles": sorted(registry.keys()),
        "required_roles": sorted(role.value for role in AgentRole),
        "forbidden_actions": sorted(FORBIDDEN_ROLE_ACTIONS),
        "forbidden_path_prefixes": list(FORBIDDEN_ROLE_PATH_PREFIXES),
        "high_risk_path_prefixes": list(HIGH_RISK_ROLE_PATH_PREFIXES),
        "safe_flags": dict(SAFE_ROLE_FLAGS),
        "role_contracts": {role_id: role.to_dict() for role_id, role in registry.items()},
        "scope": "role_registry_only_no_workflow_no_validator_no_ci_no_execution",
    }


def validate_agent_role_registry(registry: Mapping[str, AgentRoleContract] | None = None) -> dict[str, Any]:
    registry = dict(registry or build_agent_role_registry())
    required_roles = {role.value for role in AgentRole}
    blockers: list[str] = []

    missing = required_roles - set(registry)
    extra = set(registry) - required_roles
    if missing:
        blockers.append("ROLE_REGISTRY_MISSING_REQUIRED_ROLE")
    if extra:
        blockers.append("ROLE_REGISTRY_HAS_UNKNOWN_ROLE")

    for role_id, contract in registry.items():
        if contract.role_id != role_id:
            blockers.append("ROLE_ID_MISMATCH")
        if not contract.required_outputs:
            blockers.append("ROLE_REQUIRED_OUTPUTS_MISSING")
        if any(action in FORBIDDEN_ROLE_ACTIONS for action in contract.allowed_actions):
            blockers.append("ROLE_ALLOWS_FORBIDDEN_ACTION")
        if contract.allowed_for_runtime_wiring:
            blockers.append("ROLE_ALLOWS_RUNTIME_WIRING")
        if contract.allowed_for_broker_api:
            blockers.append("ROLE_ALLOWS_BROKER_API")
        if contract.allowed_for_live_execution:
            blockers.append("ROLE_ALLOWS_LIVE_EXECUTION")
        if contract.is_order_action:
            blockers.append("ROLE_IS_ORDER_ACTION")
        if contract.broker_api_called:
            blockers.append("ROLE_BROKER_API_CALLED")
        if contract.live_mode_touched:
            blockers.append("ROLE_LIVE_MODE_TOUCHED")
        if contract.real_order_id is not None:
            blockers.append("ROLE_REAL_ORDER_ID_NOT_NULL")

    return {
        "contract": AGENT_ROLE_REGISTRY_CONTRACT,
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "role_count": len(registry),
        **SAFE_ROLE_FLAGS,
    }

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agent_system.work_contract import (
    AGENT_WORK_SCHEMA_VERSION,
    FORBIDDEN_AGENT_ACTIONS,
    AgentAction,
    AgentRiskLevel,
    AgentSource,
    AgentWorkRequest,
    build_agent_work_id,
)


FORBIDDEN_PATH_PREFIXES = (
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

HIGH_RISK_PATH_PREFIXES = (
    "broker_contract/",
    "execution_safety/",
    "execution_readiness/",
    "paper_trading/",
    "core/risk",
    "core/execution",
    "config/",
    "main.py",
    "run_live.sh",
)

LOW_RISK_PATH_PREFIXES = (
    "docs/",
    "tests/",
)

SOURCE_ALLOWED_ACTIONS = {
    AgentSource.GRILL_ME.value: frozenset(
        {
            AgentAction.CRITIQUE_SCOPE.value,
            AgentAction.REVIEW_PR.value,
            AgentAction.AUDIT_RISK.value,
            AgentAction.FIND_FAKE_PROGRESS.value,
        }
    ),
    AgentSource.HERMES.value: frozenset(
        {
            AgentAction.DESIGN_ARCHITECTURE.value,
            AgentAction.DEFINE_CONTRACT.value,
            AgentAction.MAP_WORKFLOW.value,
            AgentAction.CREATE_ACCEPTANCE_GATES.value,
            AgentAction.UPDATE_DOCS.value,
        }
    ),
    AgentSource.GSD.value: frozenset(
        {
            AgentAction.PLAN_PR.value,
            AgentAction.GENERATE_TESTS.value,
            AgentAction.GENERATE_PATCH.value,
            AgentAction.FIX_TEST_FAILURE.value,
            AgentAction.UPDATE_DOCS.value,
        }
    ),
    AgentSource.MANUAL.value: frozenset(action.value for action in AgentAction),
}


@dataclass(frozen=True)
class AgentScopeDecision:
    schema_version: int
    work_id: str | None
    accepted: bool
    state: str
    source_agent: str
    action: str
    risk_level: str
    read_only: bool
    is_order_action: bool
    broker_api_called: bool
    live_mode_touched: bool
    allowed_for_patch: bool
    allowed_for_runtime_wiring: bool
    allowed_for_broker_api: bool
    allowed_for_live_execution: bool
    requires_human_approval: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    reasons: tuple[str, ...]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        payload["warnings"] = list(self.warnings)
        payload["reasons"] = list(self.reasons)
        payload["metadata"] = dict(self.metadata)
        return payload


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def _starts_with_any(path: str, prefixes: tuple[str, ...]) -> bool:
    normalized = _normalize_path(path)
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in prefixes)


def _outside_allowed_paths(path: str, allowed_paths: tuple[str, ...]) -> bool:
    if not allowed_paths:
        return False
    normalized = _normalize_path(path)
    return not any(normalized == allowed.rstrip("/") or normalized.startswith(allowed) for allowed in allowed_paths)


def _contains_order_action(action: str) -> bool:
    return action in {
        AgentAction.PLACE_ORDER.value,
        AgentAction.MODIFY_ORDER.value,
        AgentAction.CANCEL_ORDER.value,
        AgentAction.EXIT_POSITION.value,
    }


def _contains_broker_api_action(action: str) -> bool:
    return action in {
        AgentAction.CALL_BROKER_API.value,
        AgentAction.CHANGE_BROKER_CONFIG.value,
    }


def _contains_live_action(action: str) -> bool:
    return action in {
        AgentAction.ENABLE_LIVE.value,
        AgentAction.CHANGE_LIVE_CONFIG.value,
    }


def agent_scope_guard_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": "agent_scope_guard_v1",
        "source_allowed_actions": {key: sorted(value) for key, value in SOURCE_ALLOWED_ACTIONS.items()},
        "forbidden_actions": sorted(FORBIDDEN_AGENT_ACTIONS),
        "forbidden_path_prefixes": list(FORBIDDEN_PATH_PREFIXES),
        "high_risk_path_prefixes": list(HIGH_RISK_PATH_PREFIXES),
        "low_risk_path_prefixes": list(LOW_RISK_PATH_PREFIXES),
        "safe_defaults": {
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_runtime_wiring": False,
            "allowed_for_broker_api": False,
            "allowed_for_live_execution": False,
        },
        "scope": "scope_guard_only_no_api_no_ui_no_broker_no_live_no_paper_orders",
    }


def assess_agent_scope(request: AgentWorkRequest) -> AgentScopeDecision:
    blockers: list[str] = []
    warnings: list[str] = []
    reasons: list[str] = []

    source = request.source_agent
    action = request.action

    if source not in SOURCE_ALLOWED_ACTIONS:
        blockers.append("SOURCE_AGENT_UNKNOWN")
    elif action not in SOURCE_ALLOWED_ACTIONS[source]:
        blockers.append("ACTION_NOT_ALLOWED_FOR_SOURCE_AGENT")

    if action in FORBIDDEN_AGENT_ACTIONS:
        blockers.append("ACTION_FORBIDDEN")

    if _contains_order_action(action):
        blockers.append("ORDER_ACTION_FORBIDDEN")

    if _contains_broker_api_action(action):
        blockers.append("BROKER_API_FORBIDDEN")

    if _contains_live_action(action):
        blockers.append("LIVE_ACTION_FORBIDDEN")

    if not request.requested_paths:
        blockers.append("REQUESTED_PATHS_MISSING")

    for path in request.requested_paths:
        normalized = _normalize_path(path)
        if _starts_with_any(normalized, FORBIDDEN_PATH_PREFIXES):
            blockers.append("FORBIDDEN_PATH_REQUESTED")
        if normalized in {_normalize_path(item) for item in request.forbidden_paths}:
            blockers.append("REQUESTED_PATH_EXPLICITLY_FORBIDDEN")
        if _outside_allowed_paths(normalized, request.allowed_paths):
            blockers.append("REQUESTED_PATH_OUTSIDE_ALLOWED_PATHS")

    touches_high_risk = any(_starts_with_any(path, HIGH_RISK_PATH_PREFIXES) for path in request.requested_paths)
    docs_or_tests_only = bool(request.requested_paths) and all(
        _starts_with_any(path, LOW_RISK_PATH_PREFIXES) for path in request.requested_paths
    )

    if blockers:
        risk_level = AgentRiskLevel.BLOCKED.value
        state = "BLOCKED"
        allowed_for_patch = False
        requires_human_approval = True
        reasons.append("agent_scope_blocked")
        work_id = None
    elif touches_high_risk:
        risk_level = AgentRiskLevel.HIGH.value
        state = "WAITING_HUMAN_APPROVAL"
        allowed_for_patch = False
        requires_human_approval = True
        warnings.append("HIGH_RISK_PATH_REQUIRES_HUMAN_APPROVAL")
        reasons.append("high_risk_scope_requires_human_approval")
        work_id = build_agent_work_id(request)
    elif docs_or_tests_only:
        risk_level = AgentRiskLevel.LOW.value
        state = "APPROVED_FOR_PATCH"
        allowed_for_patch = True
        requires_human_approval = False
        reasons.append("low_risk_docs_or_tests_scope_approved")
        work_id = build_agent_work_id(request)
    else:
        risk_level = AgentRiskLevel.MEDIUM.value
        state = "WAITING_HUMAN_APPROVAL"
        allowed_for_patch = False
        requires_human_approval = True
        reasons.append("medium_risk_scope_requires_human_approval")
        work_id = build_agent_work_id(request)

    return AgentScopeDecision(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        work_id=work_id,
        accepted=not blockers,
        state=state,
        source_agent=source,
        action=action,
        risk_level=risk_level,
        read_only=True,
        is_order_action=False,
        broker_api_called=False,
        live_mode_touched=False,
        allowed_for_patch=allowed_for_patch,
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        allowed_for_live_execution=False,
        requires_human_approval=requires_human_approval,
        blockers=tuple(sorted(set(blockers))),
        warnings=tuple(sorted(set(warnings))),
        reasons=tuple(sorted(set(reasons))),
        metadata={
            "contract": "agent_scope_guard_v1",
            "scope": "agent_work_intake_guard_only_no_execution",
        },
    )

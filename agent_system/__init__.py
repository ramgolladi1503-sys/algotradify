"""Agent intake foundation contracts and guards.

This package is intentionally isolated from API, dashboard, broker, live, and paper-trading
runtime code. Agent PR 2 adds scope assessment only; it still performs no execution.
"""

from agent_system.scope_guard import (
    FORBIDDEN_PATH_PREFIXES,
    HIGH_RISK_PATH_PREFIXES,
    LOW_RISK_PATH_PREFIXES,
    SOURCE_ALLOWED_ACTIONS,
    AgentScopeDecision,
    agent_scope_guard_schema_contract,
    assess_agent_scope,
)
from agent_system.work_contract import (
    AGENT_WORK_SCHEMA_VERSION,
    FORBIDDEN_AGENT_ACTIONS,
    SAFE_AGENT_ACTIONS,
    AgentAction,
    AgentRiskLevel,
    AgentSource,
    AgentWorkRequest,
    AgentWorkValidationError,
    agent_work_schema_contract,
    build_agent_work_id,
    normalize_agent_work_request,
)

__all__ = [
    "AGENT_WORK_SCHEMA_VERSION",
    "FORBIDDEN_AGENT_ACTIONS",
    "FORBIDDEN_PATH_PREFIXES",
    "HIGH_RISK_PATH_PREFIXES",
    "LOW_RISK_PATH_PREFIXES",
    "SAFE_AGENT_ACTIONS",
    "SOURCE_ALLOWED_ACTIONS",
    "AgentAction",
    "AgentRiskLevel",
    "AgentScopeDecision",
    "AgentSource",
    "AgentWorkRequest",
    "AgentWorkValidationError",
    "agent_scope_guard_schema_contract",
    "agent_work_schema_contract",
    "assess_agent_scope",
    "build_agent_work_id",
    "normalize_agent_work_request",
]

"""Agent intake foundation contracts.

This package is intentionally isolated from API, dashboard, broker, live, and paper-trading
runtime code. Agent PR 1 only defines deterministic contracts.
"""

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
    "SAFE_AGENT_ACTIONS",
    "AgentAction",
    "AgentRiskLevel",
    "AgentSource",
    "AgentWorkRequest",
    "AgentWorkValidationError",
    "agent_work_schema_contract",
    "build_agent_work_id",
    "normalize_agent_work_request",
]

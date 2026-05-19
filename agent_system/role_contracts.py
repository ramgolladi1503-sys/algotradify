from __future__ import annotations

from agent_system.role_registry import (
    AGENT_ROLE_REGISTRY_CONTRACT,
    FORBIDDEN_ROLE_ACTIONS,
    FORBIDDEN_ROLE_PATH_PREFIXES,
    HIGH_RISK_ROLE_PATH_PREFIXES,
    SAFE_ROLE_FLAGS,
    AgentRole,
    AgentRoleContract,
    agent_role_registry_schema_contract,
    build_agent_role_registry,
)


__all__ = [
    "AGENT_ROLE_REGISTRY_CONTRACT",
    "FORBIDDEN_ROLE_ACTIONS",
    "FORBIDDEN_ROLE_PATH_PREFIXES",
    "HIGH_RISK_ROLE_PATH_PREFIXES",
    "SAFE_ROLE_FLAGS",
    "AgentRole",
    "AgentRoleContract",
    "agent_role_registry_schema_contract",
    "build_agent_role_registry",
]

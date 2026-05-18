"""Agent intake foundation contracts, guards, approval, and evidence.

This package is intentionally isolated from API, dashboard, broker, live, and paper-trading
runtime code. Agent PR 3 adds patch-only approval decisions and local audit evidence only;
it still performs no execution.
"""

from agent_system.approval import (
    AgentApprovalDecision,
    agent_approval_schema_contract,
    approve_agent_work,
)
from agent_system.evidence import (
    AgentEvidenceError,
    agent_evidence_schema_contract,
    build_agent_evidence_payload,
    write_agent_evidence,
)
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
    "AgentApprovalDecision",
    "AgentEvidenceError",
    "AgentRiskLevel",
    "AgentScopeDecision",
    "AgentSource",
    "AgentWorkRequest",
    "AgentWorkValidationError",
    "agent_approval_schema_contract",
    "agent_evidence_schema_contract",
    "agent_scope_guard_schema_contract",
    "agent_work_schema_contract",
    "approve_agent_work",
    "assess_agent_scope",
    "build_agent_evidence_payload",
    "build_agent_work_id",
    "normalize_agent_work_request",
    "write_agent_evidence",
]

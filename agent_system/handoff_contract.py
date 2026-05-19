from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from agent_system.role_registry import AgentRole, SAFE_ROLE_FLAGS, get_agent_role_contract
from agent_system.workflow_state import AgentWorkflowState
from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION


AGENT_HANDOFF_CONTRACT = "agent_role_handoff_artifact_v1"


class AgentHandoffVerdict(str, Enum):
    APPROVED = "APPROVED"
    APPROVED_WITH_WARNINGS = "APPROVED_WITH_WARNINGS"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


REQUIRED_HANDOFF_FIELDS = (
    "schema_version",
    "contract",
    "task_id",
    "role_id",
    "workflow_state",
    "target_state",
    "scope_decision",
    "files_allowed",
    "files_forbidden",
    "risks_found",
    "tests_required",
    "acceptance_gates",
    "required_outputs",
    "verdict",
    "safe_flags",
)

HANDOFF_LIST_FIELDS = (
    "files_allowed",
    "files_forbidden",
    "risks_found",
    "tests_required",
    "acceptance_gates",
    "required_outputs",
    "blockers",
    "warnings",
)

REQUIRED_SAFE_FLAGS = {
    **SAFE_ROLE_FLAGS,
    "allowed_for_runtime_wiring": False,
    "allowed_for_broker_api": False,
}


class AgentHandoffValidationError(ValueError):
    """Raised when a single handoff artifact payload violates the contract."""


@dataclass(frozen=True)
class AgentHandoffArtifact:
    schema_version: int
    contract: str
    task_id: str
    role_id: str
    workflow_state: str
    target_state: str
    scope_decision: str
    files_allowed: tuple[str, ...]
    files_forbidden: tuple[str, ...]
    risks_found: tuple[str, ...]
    tests_required: tuple[str, ...]
    acceptance_gates: tuple[str, ...]
    required_outputs: tuple[str, ...]
    verdict: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    safe_flags: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in HANDOFF_LIST_FIELDS:
            payload[key] = list(getattr(self, key))
        payload["safe_flags"] = dict(self.safe_flags)
        payload["metadata"] = dict(self.metadata)
        return payload


def _require_mapping(payload: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise AgentHandoffValidationError("HANDOFF_PAYLOAD_MUST_BE_OBJECT")
    return payload


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise AgentHandoffValidationError(f"{key.upper()}_MUST_BE_STRING")
    cleaned = value.strip()
    if not cleaned:
        raise AgentHandoffValidationError(f"{key.upper()}_MISSING")
    return cleaned


def _required_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise AgentHandoffValidationError(f"{key.upper()}_MUST_BE_INTEGER")
    return value


def _string_tuple(payload: Mapping[str, Any], key: str, *, required: bool = True) -> tuple[str, ...]:
    value = payload.get(key)
    if value is None:
        value = []
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise AgentHandoffValidationError(f"{key.upper()}_MUST_BE_LIST")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise AgentHandoffValidationError(f"{key.upper()}_ITEM_MUST_BE_STRING")
        cleaned = item.strip().replace("\\", "/")
        if cleaned:
            normalized.append(cleaned)
    if required and not normalized:
        raise AgentHandoffValidationError(f"{key.upper()}_MISSING")
    return tuple(normalized)


def _metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = payload.get("metadata", {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise AgentHandoffValidationError("METADATA_MUST_BE_OBJECT")
    return dict(value)


def _normalize_role(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    allowed = {role.value for role in AgentRole}
    if normalized not in allowed:
        raise AgentHandoffValidationError("ROLE_ID_UNKNOWN")
    return normalized


def _normalize_state(value: str) -> str:
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    allowed = {state.value for state in AgentWorkflowState}
    if normalized not in allowed:
        raise AgentHandoffValidationError("WORKFLOW_STATE_UNKNOWN")
    return normalized


def _normalize_verdict(value: str) -> str:
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    allowed = {verdict.value for verdict in AgentHandoffVerdict}
    if normalized not in allowed:
        raise AgentHandoffValidationError("VERDICT_UNKNOWN")
    return normalized


def _safe_flags(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = payload.get("safe_flags")
    if not isinstance(value, Mapping):
        raise AgentHandoffValidationError("SAFE_FLAGS_MUST_BE_OBJECT")
    flags = dict(value)
    for key, expected in REQUIRED_SAFE_FLAGS.items():
        if flags.get(key) != expected:
            raise AgentHandoffValidationError(f"SAFE_FLAG_{key.upper()}_INVALID")
    return {key: flags.get(key) for key in REQUIRED_SAFE_FLAGS}


def _require_all_fields(payload: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_HANDOFF_FIELDS if field not in payload]
    if missing:
        raise AgentHandoffValidationError("HANDOFF_REQUIRED_FIELDS_MISSING:" + ",".join(sorted(missing)))


def normalize_agent_handoff_artifact(payload: Mapping[str, Any] | Any) -> AgentHandoffArtifact:
    """Normalize and validate one role handoff artifact payload.

    PR 13 deliberately validates a single in-memory payload only. It does not scan
    docs/pr-handoffs, compare changed files, run CI, or decide merge-readiness.
    """

    raw = _require_mapping(payload)
    _require_all_fields(raw)

    schema_version = _required_int(raw, "schema_version")
    if schema_version != AGENT_WORK_SCHEMA_VERSION:
        raise AgentHandoffValidationError("SCHEMA_VERSION_UNSUPPORTED")

    contract = _required_string(raw, "contract")
    if contract != AGENT_HANDOFF_CONTRACT:
        raise AgentHandoffValidationError("CONTRACT_UNSUPPORTED")

    role_id = _normalize_role(_required_string(raw, "role_id"))
    role_contract = get_agent_role_contract(role_id)
    required_outputs = _string_tuple(raw, "required_outputs")
    missing_role_outputs = sorted(set(role_contract.required_outputs) - set(required_outputs))
    if missing_role_outputs:
        raise AgentHandoffValidationError("ROLE_REQUIRED_OUTPUTS_MISSING:" + ",".join(missing_role_outputs))

    artifact = AgentHandoffArtifact(
        schema_version=schema_version,
        contract=contract,
        task_id=_required_string(raw, "task_id"),
        role_id=role_id,
        workflow_state=_normalize_state(_required_string(raw, "workflow_state")),
        target_state=_normalize_state(_required_string(raw, "target_state")),
        scope_decision=_required_string(raw, "scope_decision"),
        files_allowed=_string_tuple(raw, "files_allowed"),
        files_forbidden=_string_tuple(raw, "files_forbidden"),
        risks_found=_string_tuple(raw, "risks_found"),
        tests_required=_string_tuple(raw, "tests_required"),
        acceptance_gates=_string_tuple(raw, "acceptance_gates"),
        required_outputs=required_outputs,
        verdict=_normalize_verdict(_required_string(raw, "verdict")),
        blockers=_string_tuple(raw, "blockers", required=False),
        warnings=_string_tuple(raw, "warnings", required=False),
        safe_flags=_safe_flags(raw),
        metadata={
            **_metadata(raw),
            "scope": "handoff_artifact_contract_only_no_repo_scan_no_ci_no_execution",
        },
    )

    if artifact.verdict in {AgentHandoffVerdict.REJECTED.value, AgentHandoffVerdict.BLOCKED.value} and not artifact.blockers:
        raise AgentHandoffValidationError("BLOCKING_VERDICT_REQUIRES_BLOCKERS")

    return artifact


def build_minimal_handoff_payload(
    *,
    task_id: str,
    role_id: str,
    workflow_state: str,
    target_state: str,
    scope_decision: str = "APPROVED_WITH_STRICT_SCOPE",
    verdict: str = AgentHandoffVerdict.APPROVED.value,
) -> dict[str, Any]:
    """Build a minimal valid payload for one role.

    This helper is deterministic test/support data only. It does not write files.
    """

    role = get_agent_role_contract(_normalize_role(role_id))
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": AGENT_HANDOFF_CONTRACT,
        "task_id": task_id,
        "role_id": role.role_id,
        "workflow_state": workflow_state,
        "target_state": target_state,
        "scope_decision": scope_decision,
        "files_allowed": list(role.allowed_path_prefixes),
        "files_forbidden": list(role.forbidden_path_prefixes),
        "risks_found": ["scope_drift"],
        "tests_required": ["behavior_tests"],
        "acceptance_gates": ["safe_flags_preserved"],
        "required_outputs": list(role.required_outputs),
        "verdict": verdict,
        "blockers": [],
        "warnings": [],
        "safe_flags": dict(REQUIRED_SAFE_FLAGS),
        "metadata": {"generated_by": "build_minimal_handoff_payload"},
    }


def agent_handoff_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": AGENT_HANDOFF_CONTRACT,
        "required_fields": list(REQUIRED_HANDOFF_FIELDS),
        "list_fields": list(HANDOFF_LIST_FIELDS),
        "verdicts": sorted(verdict.value for verdict in AgentHandoffVerdict),
        "roles": sorted(role.value for role in AgentRole),
        "workflow_states": sorted(state.value for state in AgentWorkflowState),
        "required_safe_flags": dict(REQUIRED_SAFE_FLAGS),
        "scope": "handoff_artifact_contract_only_no_validator_no_ci_no_execution",
    }


def validate_agent_handoff_payload(payload: Mapping[str, Any] | Any) -> dict[str, Any]:
    try:
        artifact = normalize_agent_handoff_artifact(payload)
    except AgentHandoffValidationError as exc:
        return {
            "contract": AGENT_HANDOFF_CONTRACT,
            "valid": False,
            "error": str(exc),
            **REQUIRED_SAFE_FLAGS,
        }
    return {
        "contract": AGENT_HANDOFF_CONTRACT,
        "valid": True,
        "task_id": artifact.task_id,
        "role_id": artifact.role_id,
        "workflow_state": artifact.workflow_state,
        "target_state": artifact.target_state,
        "verdict": artifact.verdict,
        **REQUIRED_SAFE_FLAGS,
    }

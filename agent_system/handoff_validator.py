from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent_system.handoff_contract import (
    AGENT_HANDOFF_CONTRACT,
    AgentHandoffArtifact,
    AgentHandoffValidationError,
    normalize_agent_handoff_artifact,
)
from agent_system.role_registry import SAFE_ROLE_FLAGS, AgentRole
from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION


AGENT_HANDOFF_VALIDATOR_CONTRACT = "agent_handoff_evidence_validator_v1"

HANDOFF_JSON_BLOCK_RE = re.compile(r"```json\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)

DEFAULT_REQUIRED_HANDOFF_ROLES = (
    AgentRole.SCOPE_OWNER.value,
    AgentRole.GRILL_REVIEWER.value,
    AgentRole.HERMES_ARCHITECT.value,
    AgentRole.GSD_IMPLEMENTER.value,
    AgentRole.QA_SAFETY_REVIEWER.value,
    AgentRole.EVIDENCE_RECORDER.value,
)

ROLE_FILE_SUFFIXES = {
    AgentRole.SCOPE_OWNER.value: "scope-owner",
    AgentRole.GRILL_REVIEWER.value: "grill",
    AgentRole.HERMES_ARCHITECT.value: "hermes",
    AgentRole.GSD_IMPLEMENTER.value: "gsd",
    AgentRole.QA_SAFETY_REVIEWER.value: "qa-safety",
    AgentRole.EVIDENCE_RECORDER.value: "evidence",
}

REQUIRED_VALIDATOR_SAFE_FLAGS = {
    **SAFE_ROLE_FLAGS,
    "allowed_for_runtime_wiring": False,
    "allowed_for_broker_api": False,
}


@dataclass(frozen=True)
class HandoffFileResult:
    path: str
    role_id: str | None
    task_id: str | None
    valid: bool
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HandoffValidationReport:
    schema_version: int
    contract: str
    task_id: str
    valid: bool
    handoff_dir: str
    required_roles: tuple[str, ...]
    roles_found: tuple[str, ...]
    missing_roles: tuple[str, ...]
    missing_files: tuple[str, ...]
    blockers: tuple[str, ...]
    file_results: tuple[HandoffFileResult, ...]
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
        payload["required_roles"] = list(self.required_roles)
        payload["roles_found"] = list(self.roles_found)
        payload["missing_roles"] = list(self.missing_roles)
        payload["missing_files"] = list(self.missing_files)
        payload["blockers"] = list(self.blockers)
        payload["file_results"] = [result.to_dict() for result in self.file_results]
        payload["metadata"] = dict(self.metadata)
        return payload


def expected_handoff_paths(task_id: str, handoff_dir: str | Path, required_roles: Sequence[str] | None = None) -> dict[str, Path]:
    clean_task_id = _clean_task_id(task_id)
    root = Path(handoff_dir)
    roles = tuple(required_roles or DEFAULT_REQUIRED_HANDOFF_ROLES)
    return {
        role: root / f"{clean_task_id}-{ROLE_FILE_SUFFIXES[role]}.md"
        for role in roles
    }


def _clean_task_id(task_id: str) -> str:
    cleaned = task_id.strip()
    if not cleaned:
        raise ValueError("TASK_ID_MISSING")
    if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
        raise ValueError("TASK_ID_UNSAFE")
    return cleaned


def _normalize_required_roles(required_roles: Sequence[str] | None) -> tuple[str, ...]:
    roles = tuple(required_roles or DEFAULT_REQUIRED_HANDOFF_ROLES)
    normalized: list[str] = []
    allowed = set(ROLE_FILE_SUFFIXES)
    for role in roles:
        clean = str(role).strip().lower().replace("-", "_").replace(" ", "_")
        if clean not in allowed:
            raise ValueError(f"UNKNOWN_REQUIRED_HANDOFF_ROLE:{role}")
        normalized.append(clean)
    return tuple(normalized)


def extract_handoff_payload_from_markdown(content: str) -> Mapping[str, Any]:
    for match in HANDOFF_JSON_BLOCK_RE.finditer(content):
        raw_json = match.group(1).strip()
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping) and payload.get("contract") == AGENT_HANDOFF_CONTRACT:
            return payload
    raise AgentHandoffValidationError("HANDOFF_JSON_PAYLOAD_NOT_FOUND")


def load_handoff_artifact(path: str | Path) -> AgentHandoffArtifact:
    file_path = Path(path)
    if not file_path.exists():
        raise AgentHandoffValidationError("HANDOFF_FILE_MISSING")
    if not file_path.is_file():
        raise AgentHandoffValidationError("HANDOFF_PATH_NOT_FILE")
    payload = extract_handoff_payload_from_markdown(file_path.read_text(encoding="utf-8"))
    return normalize_agent_handoff_artifact(payload)


def validate_handoff_evidence(
    *,
    task_id: str,
    handoff_dir: str | Path = "docs/pr-handoffs",
    required_roles: Sequence[str] | None = None,
) -> HandoffValidationReport:
    """Validate required role handoff artifacts for one task.

    PR 14 validates evidence files only. It does not inspect changed files, call GitHub,
    update CI, approve merges, or execute broker/runtime behavior.
    """

    clean_task_id = _clean_task_id(task_id)
    roles = _normalize_required_roles(required_roles)
    expected_paths = expected_handoff_paths(clean_task_id, handoff_dir, roles)
    file_results: list[HandoffFileResult] = []
    roles_found: list[str] = []
    missing_files: list[str] = []
    blockers: list[str] = []

    for expected_role, path in expected_paths.items():
        try:
            artifact = load_handoff_artifact(path)
            role_id = artifact.role_id
            artifact_task_id = artifact.task_id
            if artifact.task_id != clean_task_id:
                blockers.append("HANDOFF_TASK_ID_MISMATCH")
                file_results.append(
                    HandoffFileResult(
                        path=str(path),
                        role_id=role_id,
                        task_id=artifact_task_id,
                        valid=False,
                        error="HANDOFF_TASK_ID_MISMATCH",
                    )
                )
                continue
            if artifact.role_id != expected_role:
                blockers.append("HANDOFF_ROLE_ID_MISMATCH")
                file_results.append(
                    HandoffFileResult(
                        path=str(path),
                        role_id=role_id,
                        task_id=artifact_task_id,
                        valid=False,
                        error="HANDOFF_ROLE_ID_MISMATCH",
                    )
                )
                continue
            roles_found.append(role_id)
            file_results.append(
                HandoffFileResult(
                    path=str(path),
                    role_id=role_id,
                    task_id=artifact_task_id,
                    valid=True,
                    error=None,
                )
            )
        except AgentHandoffValidationError as exc:
            if str(exc) == "HANDOFF_FILE_MISSING":
                missing_files.append(str(path))
                blockers.append("HANDOFF_FILE_MISSING")
            else:
                blockers.append("HANDOFF_FILE_INVALID")
            file_results.append(
                HandoffFileResult(
                    path=str(path),
                    role_id=None,
                    task_id=None,
                    valid=False,
                    error=str(exc),
                )
            )

    missing_roles = tuple(role for role in roles if role not in roles_found)
    if missing_roles:
        blockers.append("HANDOFF_REQUIRED_ROLE_MISSING")

    return HandoffValidationReport(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        contract=AGENT_HANDOFF_VALIDATOR_CONTRACT,
        task_id=clean_task_id,
        valid=not blockers,
        handoff_dir=str(handoff_dir),
        required_roles=roles,
        roles_found=tuple(sorted(set(roles_found))),
        missing_roles=missing_roles,
        missing_files=tuple(missing_files),
        blockers=tuple(sorted(set(blockers))),
        file_results=tuple(file_results),
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        metadata={
            "scope": "handoff_evidence_validator_only_no_ci_no_changed_file_audit_no_execution",
            "expected_paths": {role: str(path) for role, path in expected_paths.items()},
        },
        **SAFE_ROLE_FLAGS,
    )


def agent_handoff_validator_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": AGENT_HANDOFF_VALIDATOR_CONTRACT,
        "required_roles": list(DEFAULT_REQUIRED_HANDOFF_ROLES),
        "role_file_suffixes": dict(ROLE_FILE_SUFFIXES),
        "required_safe_flags": dict(REQUIRED_VALIDATOR_SAFE_FLAGS),
        "payload_contract": AGENT_HANDOFF_CONTRACT,
        "scope": "handoff_evidence_validator_only_no_ci_no_changed_file_audit_no_execution",
    }


def report_to_json(report: HandoffValidationReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)

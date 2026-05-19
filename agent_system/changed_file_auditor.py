from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from agent_system.handoff_contract import AgentHandoffArtifact, AgentHandoffValidationError
from agent_system.handoff_validator import expected_handoff_paths, load_handoff_artifact
from agent_system.role_registry import HIGH_RISK_ROLE_PATH_PREFIXES, SAFE_ROLE_FLAGS, AgentRole
from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION


AGENT_CHANGED_FILE_AUDITOR_CONTRACT = "agent_changed_file_scope_auditor_v1"

DEFAULT_SCOPE_APPROVAL_ROLES = (
    AgentRole.SCOPE_OWNER.value,
    AgentRole.HERMES_ARCHITECT.value,
    AgentRole.GSD_IMPLEMENTER.value,
)

REQUIRED_AUDITOR_SAFE_FLAGS = {
    **SAFE_ROLE_FLAGS,
    "allowed_for_runtime_wiring": False,
    "allowed_for_broker_api": False,
}


@dataclass(frozen=True)
class ChangedFileFinding:
    path: str
    accepted: bool
    blockers: tuple[str, ...]
    matched_allowed_roles: tuple[str, ...]
    matched_forbidden_roles: tuple[str, ...]
    high_risk: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        payload["matched_allowed_roles"] = list(self.matched_allowed_roles)
        payload["matched_forbidden_roles"] = list(self.matched_forbidden_roles)
        return payload


@dataclass(frozen=True)
class ChangedFileAuditReport:
    schema_version: int
    contract: str
    task_id: str
    valid: bool
    changed_files: tuple[str, ...]
    scope_roles: tuple[str, ...]
    blockers: tuple[str, ...]
    findings: tuple[ChangedFileFinding, ...]
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
        payload["changed_files"] = list(self.changed_files)
        payload["scope_roles"] = list(self.scope_roles)
        payload["blockers"] = list(self.blockers)
        payload["findings"] = [finding.to_dict() for finding in self.findings]
        payload["metadata"] = dict(self.metadata)
        return payload


def normalize_changed_file_path(path: str) -> str:
    normalized = str(path).strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        raise ValueError("CHANGED_FILE_PATH_MISSING")
    if normalized.startswith("/") or ".." in normalized.split("/"):
        raise ValueError("CHANGED_FILE_PATH_UNSAFE")
    return normalized


def path_matches_rule(path: str, rule: str) -> bool:
    changed_path = normalize_changed_file_path(path)
    normalized_rule = str(rule).strip().replace("\\", "/")
    while normalized_rule.startswith("./"):
        normalized_rule = normalized_rule[2:]
    if not normalized_rule:
        return False
    if normalized_rule.endswith("/"):
        return changed_path.startswith(normalized_rule)
    return changed_path == normalized_rule or changed_path.startswith(normalized_rule.rstrip("/") + "/")


def _clean_task_id(task_id: str) -> str:
    cleaned = task_id.strip()
    if not cleaned:
        raise ValueError("TASK_ID_MISSING")
    if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
        raise ValueError("TASK_ID_UNSAFE")
    return cleaned


def _normalize_scope_roles(scope_roles: Sequence[str] | None) -> tuple[str, ...]:
    roles = tuple(scope_roles or DEFAULT_SCOPE_APPROVAL_ROLES)
    allowed = {role.value for role in AgentRole}
    normalized: list[str] = []
    for role in roles:
        clean = str(role).strip().lower().replace("-", "_").replace(" ", "_")
        if clean not in allowed:
            raise ValueError(f"UNKNOWN_SCOPE_ROLE:{role}")
        normalized.append(clean)
    return tuple(normalized)


def _load_scope_artifacts(task_id: str, handoff_dir: str | Path, scope_roles: tuple[str, ...]) -> tuple[AgentHandoffArtifact, ...]:
    paths = expected_handoff_paths(task_id, handoff_dir, required_roles=scope_roles)
    artifacts: list[AgentHandoffArtifact] = []
    for role in scope_roles:
        artifact = load_handoff_artifact(paths[role])
        if artifact.task_id != task_id:
            raise AgentHandoffValidationError("HANDOFF_TASK_ID_MISMATCH")
        if artifact.role_id != role:
            raise AgentHandoffValidationError("HANDOFF_ROLE_ID_MISMATCH")
        artifacts.append(artifact)
    return tuple(artifacts)


def audit_changed_files_against_handoffs(
    *,
    task_id: str,
    changed_files: Sequence[str],
    handoff_dir: str | Path = "docs/pr-handoffs",
    scope_roles: Sequence[str] | None = None,
    human_approved: bool = False,
) -> ChangedFileAuditReport:
    """Audit changed files against approved handoff scope.

    PR 16 validates changed-file scope only. It does not enforce PR templates,
    generate architecture replay reports, call broker APIs, or mutate runtime state.
    """

    clean_task_id = _clean_task_id(task_id)
    roles = _normalize_scope_roles(scope_roles)
    blockers: list[str] = []
    findings: list[ChangedFileFinding] = []

    try:
        normalized_changed_files = tuple(normalize_changed_file_path(path) for path in changed_files)
    except ValueError as exc:
        return _blocked_report(
            task_id=clean_task_id,
            changed_files=tuple(str(path) for path in changed_files),
            scope_roles=roles,
            blockers=(str(exc),),
            findings=(),
            handoff_dir=handoff_dir,
        )

    if not normalized_changed_files:
        return _blocked_report(
            task_id=clean_task_id,
            changed_files=(),
            scope_roles=roles,
            blockers=("CHANGED_FILES_MISSING",),
            findings=(),
            handoff_dir=handoff_dir,
        )

    try:
        artifacts = _load_scope_artifacts(clean_task_id, handoff_dir, roles)
    except (AgentHandoffValidationError, ValueError) as exc:
        return _blocked_report(
            task_id=clean_task_id,
            changed_files=normalized_changed_files,
            scope_roles=roles,
            blockers=("HANDOFF_SCOPE_EVIDENCE_INVALID", str(exc)),
            findings=(),
            handoff_dir=handoff_dir,
        )

    for changed_file in normalized_changed_files:
        file_blockers: list[str] = []
        matched_allowed_roles: list[str] = []
        matched_forbidden_roles: list[str] = []

        for artifact in artifacts:
            if any(path_matches_rule(changed_file, rule) for rule in artifact.files_allowed):
                matched_allowed_roles.append(artifact.role_id)
            if any(path_matches_rule(changed_file, rule) for rule in artifact.files_forbidden):
                matched_forbidden_roles.append(artifact.role_id)

        if matched_forbidden_roles:
            file_blockers.append("CHANGED_FILE_FORBIDDEN_BY_HANDOFF")
        if set(matched_allowed_roles) != set(roles):
            file_blockers.append("CHANGED_FILE_OUTSIDE_APPROVED_SCOPE")

        high_risk = any(path_matches_rule(changed_file, prefix) for prefix in HIGH_RISK_ROLE_PATH_PREFIXES)
        if high_risk and not human_approved:
            file_blockers.append("HIGH_RISK_PATH_REQUIRES_HUMAN_APPROVAL")

        findings.append(
            ChangedFileFinding(
                path=changed_file,
                accepted=not file_blockers,
                blockers=tuple(sorted(set(file_blockers))),
                matched_allowed_roles=tuple(sorted(set(matched_allowed_roles))),
                matched_forbidden_roles=tuple(sorted(set(matched_forbidden_roles))),
                high_risk=high_risk,
            )
        )
        blockers.extend(file_blockers)

    return ChangedFileAuditReport(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        contract=AGENT_CHANGED_FILE_AUDITOR_CONTRACT,
        task_id=clean_task_id,
        valid=not blockers,
        changed_files=normalized_changed_files,
        scope_roles=roles,
        blockers=tuple(sorted(set(blockers))),
        findings=tuple(findings),
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        metadata={
            "scope": "changed_file_scope_auditor_only_no_pr_template_no_architecture_report_no_execution",
            "handoff_dir": str(handoff_dir),
            "human_approved": human_approved,
        },
        **SAFE_ROLE_FLAGS,
    )


def _blocked_report(
    *,
    task_id: str,
    changed_files: tuple[str, ...],
    scope_roles: tuple[str, ...],
    blockers: tuple[str, ...],
    findings: tuple[ChangedFileFinding, ...],
    handoff_dir: str | Path,
) -> ChangedFileAuditReport:
    return ChangedFileAuditReport(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        contract=AGENT_CHANGED_FILE_AUDITOR_CONTRACT,
        task_id=task_id,
        valid=False,
        changed_files=changed_files,
        scope_roles=scope_roles,
        blockers=tuple(sorted(set(blockers))),
        findings=findings,
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        metadata={
            "scope": "changed_file_scope_auditor_only_no_pr_template_no_architecture_report_no_execution",
            "handoff_dir": str(handoff_dir),
        },
        **SAFE_ROLE_FLAGS,
    )


def agent_changed_file_auditor_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": AGENT_CHANGED_FILE_AUDITOR_CONTRACT,
        "default_scope_roles": list(DEFAULT_SCOPE_APPROVAL_ROLES),
        "high_risk_path_prefixes": list(HIGH_RISK_ROLE_PATH_PREFIXES),
        "required_safe_flags": dict(REQUIRED_AUDITOR_SAFE_FLAGS),
        "scope": "changed_file_scope_auditor_only_no_pr_template_no_architecture_report_no_execution",
    }

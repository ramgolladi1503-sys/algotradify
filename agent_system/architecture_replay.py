from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from agent_system.architecture_gate import run_agent_architecture_gate
from agent_system.changed_file_auditor import audit_changed_files_against_handoffs
from agent_system.handoff_validator import validate_handoff_evidence
from agent_system.pr_gate import validate_pr_body_template
from agent_system.role_registry import SAFE_ROLE_FLAGS, validate_agent_role_registry
from agent_system.workflow_state import validate_agent_workflow_state_machine
from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION


AGENT_ARCHITECTURE_REPLAY_CONTRACT = "agent_architecture_replay_audit_report_v1"

REQUIRED_REPLAY_SAFE_FLAGS = {
    **SAFE_ROLE_FLAGS,
    "allowed_for_runtime_wiring": False,
    "allowed_for_broker_api": False,
}


@dataclass(frozen=True)
class ArchitectureReplaySection:
    name: str
    valid: bool
    blockers: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        return payload


@dataclass(frozen=True)
class ArchitectureReplayReport:
    schema_version: int
    contract: str
    task_id: str
    valid: bool
    sections: tuple[ArchitectureReplaySection, ...]
    blockers: tuple[str, ...]
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
        payload["sections"] = [section.to_dict() for section in self.sections]
        payload["blockers"] = list(self.blockers)
        payload["metadata"] = dict(self.metadata)
        return payload


def _section(name: str, valid: bool, blockers: Sequence[str], summary: str) -> ArchitectureReplaySection:
    return ArchitectureReplaySection(
        name=name,
        valid=valid,
        blockers=tuple(sorted(set(blockers))),
        summary=summary,
    )


def run_architecture_replay_report(
    *,
    task_ref: str,
    changed_files: Sequence[str],
    pr_body: str,
    handoff_dir: str | Path = "docs/pr-handoffs",
    human_approved: bool = False,
) -> ArchitectureReplayReport:
    """Build a deterministic architecture replay/audit report.

    PR 18 is reporting only. It does not mutate repository state, call external services,
    create approval decisions, or change product/runtime behavior.
    """

    architecture_gate = run_agent_architecture_gate(task_ref=task_ref, handoff_dir=handoff_dir)
    task_id = architecture_gate.task_id
    role_registry = validate_agent_role_registry()
    workflow_state = validate_agent_workflow_state_machine()
    handoff_evidence = validate_handoff_evidence(task_id=task_id, handoff_dir=handoff_dir)
    body_report = validate_pr_body_template(pr_body)
    changed_file_report = audit_changed_files_against_handoffs(
        task_id=task_id,
        changed_files=changed_files,
        handoff_dir=handoff_dir,
        human_approved=human_approved,
    )

    sections = (
        _section(
            "role_registry",
            bool(role_registry.get("valid")),
            tuple(role_registry.get("blockers", ())),
            "Role registry contract validation",
        ),
        _section(
            "workflow_state_machine",
            bool(workflow_state.get("valid")),
            tuple(workflow_state.get("blockers", ())),
            "Workflow state machine validation",
        ),
        _section(
            "handoff_evidence",
            handoff_evidence.valid,
            handoff_evidence.blockers,
            f"Handoff evidence roles found: {','.join(handoff_evidence.roles_found)}",
        ),
        _section(
            "architecture_gate",
            architecture_gate.valid,
            architecture_gate.blockers,
            "Architecture gate validation",
        ),
        _section(
            "pr_body_template",
            body_report.valid,
            tuple([*body_report.missing_sections, *body_report.missing_phrases]),
            "PR body template validation",
        ),
        _section(
            "changed_file_scope",
            changed_file_report.valid,
            changed_file_report.blockers,
            f"Changed file count: {len(changed_file_report.changed_files)}",
        ),
    )
    blockers = tuple(
        f"{section.name}:{blocker}"
        for section in sections
        for blocker in section.blockers
    )

    return ArchitectureReplayReport(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        contract=AGENT_ARCHITECTURE_REPLAY_CONTRACT,
        task_id=task_id,
        valid=all(section.valid for section in sections),
        sections=sections,
        blockers=tuple(sorted(set(blockers))),
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        metadata={
            "scope": "architecture_replay_audit_report_only_no_execution_no_product_behavior",
            "handoff_dir": str(handoff_dir),
            "changed_files": list(changed_files),
            "human_approved": human_approved,
            "final_governance_pr": "AGENT-PR18",
        },
        **SAFE_ROLE_FLAGS,
    )


def architecture_replay_report_to_markdown(report: ArchitectureReplayReport) -> str:
    status = "PASS" if report.valid else "FAIL"
    lines = [
        f"# Architecture Replay Audit Report — {report.task_id}",
        "",
        f"Overall status: **{status}**",
        "",
        "## Sections",
        "",
    ]
    for section in report.sections:
        section_status = "PASS" if section.valid else "FAIL"
        lines.extend(
            [
                f"### {section.name}",
                "",
                f"Status: **{section_status}**",
                "",
                section.summary,
                "",
            ]
        )
        if section.blockers:
            lines.append("Blockers:")
            lines.extend(f"- {blocker}" for blocker in section.blockers)
            lines.append("")
    lines.extend(
        [
            "## Safe flags",
            "",
            "```json",
            json.dumps({key: getattr(report, key) for key in REQUIRED_REPLAY_SAFE_FLAGS}, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def architecture_replay_report_to_json(report: ArchitectureReplayReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def agent_architecture_replay_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": AGENT_ARCHITECTURE_REPLAY_CONTRACT,
        "sections": [
            "role_registry",
            "workflow_state_machine",
            "handoff_evidence",
            "architecture_gate",
            "pr_body_template",
            "changed_file_scope",
        ],
        "required_safe_flags": dict(REQUIRED_REPLAY_SAFE_FLAGS),
        "scope": "architecture_replay_audit_report_only_no_execution_no_product_behavior",
    }

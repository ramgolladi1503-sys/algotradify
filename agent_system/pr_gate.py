from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from agent_system.architecture_gate import run_agent_architecture_gate
from agent_system.changed_file_auditor import audit_changed_files_against_handoffs
from agent_system.role_registry import SAFE_ROLE_FLAGS
from agent_system.work_contract import AGENT_WORK_SCHEMA_VERSION


AGENT_PR_GATE_CONTRACT = "agent_pr_template_local_developer_gate_v1"

REQUIRED_PR_BODY_SECTIONS = (
    "## Summary",
    "## Agent handoff evidence",
    "## Pre-code scope review",
    "## Files changed",
    "## Files not touched",
    "## Safety boundary",
    "## Tests added",
    "## Test commands",
    "## Acceptance proof",
    "## Post-code review",
    "## Next PR after merge",
)

REQUIRED_PR_BODY_PHRASES = (
    "Grill independent: yes",
    "GSD followed Grill scope: yes",
    "Hermes reviewed final diff: yes",
    "Files to change",
    "Files not to touch",
    "Negative tests",
    "Regression risks",
    "Changed files match approved scope: yes",
    "Forbidden files touched: no",
    "Safety boundary preserved: yes",
)

REQUIRED_GATE_SAFE_FLAGS = {
    **SAFE_ROLE_FLAGS,
    "allowed_for_runtime_wiring": False,
    "allowed_for_broker_api": False,
}


@dataclass(frozen=True)
class PrBodyCheckReport:
    valid: bool
    missing_sections: tuple[str, ...]
    missing_phrases: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["missing_sections"] = list(self.missing_sections)
        payload["missing_phrases"] = list(self.missing_phrases)
        return payload


@dataclass(frozen=True)
class AgentPrGateReport:
    schema_version: int
    contract: str
    task_id: str
    valid: bool
    blockers: tuple[str, ...]
    pr_body_valid: bool
    architecture_gate_valid: bool
    changed_file_audit_valid: bool
    changed_file_count: int
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
        payload["blockers"] = list(self.blockers)
        payload["metadata"] = dict(self.metadata)
        return payload


def validate_pr_body_template(body: str) -> PrBodyCheckReport:
    text = body or ""
    missing_sections = tuple(section for section in REQUIRED_PR_BODY_SECTIONS if section not in text)
    missing_phrases = tuple(phrase for phrase in REQUIRED_PR_BODY_PHRASES if phrase not in text)
    return PrBodyCheckReport(
        valid=not missing_sections and not missing_phrases,
        missing_sections=missing_sections,
        missing_phrases=missing_phrases,
    )


def load_text_file(path: str | Path) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise ValueError(f"FILE_MISSING:{file_path}")
    if not file_path.is_file():
        raise ValueError(f"PATH_NOT_FILE:{file_path}")
    return file_path.read_text(encoding="utf-8")


def load_changed_files(path: str | Path) -> tuple[str, ...]:
    content = load_text_file(path)
    return tuple(line.strip() for line in content.splitlines() if line.strip())


def run_agent_pr_gate(
    *,
    task_ref: str,
    changed_files: Sequence[str],
    pr_body: str,
    handoff_dir: str | Path = "docs/pr-handoffs",
    human_approved: bool = False,
) -> AgentPrGateReport:
    """Run the PR 17 local developer gate.

    This gate combines PR-body shape checks, the PR 15 architecture gate, and the
    PR 16 changed-file auditor. It does not generate PR18 architecture replay reports
    and does not call external services or mutate runtime state.
    """

    architecture_report = run_agent_architecture_gate(task_ref=task_ref, handoff_dir=handoff_dir)
    task_id = architecture_report.task_id
    body_report = validate_pr_body_template(pr_body)
    changed_report = audit_changed_files_against_handoffs(
        task_id=task_id,
        changed_files=changed_files,
        handoff_dir=handoff_dir,
        human_approved=human_approved,
    )

    blockers: list[str] = []
    if not body_report.valid:
        blockers.append("PR_BODY_TEMPLATE_INVALID")
    if not architecture_report.valid:
        blockers.extend(f"ARCHITECTURE_GATE:{blocker}" for blocker in architecture_report.blockers)
    if not changed_report.valid:
        blockers.extend(f"CHANGED_FILE_AUDIT:{blocker}" for blocker in changed_report.blockers)

    return AgentPrGateReport(
        schema_version=AGENT_WORK_SCHEMA_VERSION,
        contract=AGENT_PR_GATE_CONTRACT,
        task_id=task_id,
        valid=not blockers,
        blockers=tuple(sorted(set(blockers))),
        pr_body_valid=body_report.valid,
        architecture_gate_valid=architecture_report.valid,
        changed_file_audit_valid=changed_report.valid,
        changed_file_count=len(changed_report.changed_files),
        allowed_for_runtime_wiring=False,
        allowed_for_broker_api=False,
        metadata={
            "scope": "pr_template_local_developer_gate_only_no_architecture_replay_report_no_execution",
            "handoff_dir": str(handoff_dir),
            "missing_sections": list(body_report.missing_sections),
            "missing_phrases": list(body_report.missing_phrases),
            "architecture_blockers": list(architecture_report.blockers),
            "changed_file_blockers": list(changed_report.blockers),
            "human_approved": human_approved,
        },
        **SAFE_ROLE_FLAGS,
    )


def agent_pr_gate_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": AGENT_PR_GATE_CONTRACT,
        "required_sections": list(REQUIRED_PR_BODY_SECTIONS),
        "required_phrases": list(REQUIRED_PR_BODY_PHRASES),
        "required_checks": [
            "pr_body_valid",
            "architecture_gate_valid",
            "changed_file_audit_valid",
        ],
        "required_safe_flags": dict(REQUIRED_GATE_SAFE_FLAGS),
        "scope": "pr_template_local_developer_gate_only_no_architecture_replay_report_no_execution",
    }


def extract_changed_files_from_diff_name_output(content: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#"))


def extract_markdown_codeblock_paths(body: str, section_title: str) -> tuple[str, ...]:
    pattern = re.compile(rf"{re.escape(section_title)}\s*```text\s*(.*?)\s*```", re.DOTALL)
    match = pattern.search(body or "")
    if not match:
        return ()
    return tuple(line.strip() for line in match.group(1).splitlines() if line.strip())

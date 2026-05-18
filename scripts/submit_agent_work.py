#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_system.approval import approve_agent_work
from agent_system.evidence import AgentEvidenceError, write_agent_evidence
from agent_system.scope_guard import assess_agent_scope
from agent_system.work_contract import AgentWorkValidationError, normalize_agent_work_request


EXIT_APPROVED = 0
EXIT_REJECTED = 1
EXIT_BLOCKED = 2
EXIT_EVIDENCE_FAILED = 3


@dataclass(frozen=True)
class AgentWorkCliResult:
    exit_code: int
    status: str
    message: str
    payload: dict[str, Any]


def _read_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"payload file not found: {path}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AgentWorkValidationError("PAYLOAD_JSON_MUST_BE_OBJECT")
    return loaded


def _safe_error_result(*, status: str, message: str, exit_code: int) -> AgentWorkCliResult:
    return AgentWorkCliResult(
        exit_code=exit_code,
        status=status,
        message=message,
        payload={
            "status": status,
            "message": message,
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
        },
    )


def run_agent_work_submission(
    *,
    payload_path: str | Path,
    approve: bool = False,
    approved_by: str | None = None,
    evidence_root: str | Path = "runtime/agent_work",
) -> AgentWorkCliResult:
    """Run local agent-work submission without API, UI, broker, or execution behavior."""

    try:
        raw_payload = _read_payload(Path(payload_path))
        request = normalize_agent_work_request(raw_payload)
    except FileNotFoundError as exc:
        return _safe_error_result(status="INPUT_ERROR", message=str(exc), exit_code=EXIT_BLOCKED)
    except json.JSONDecodeError as exc:
        return _safe_error_result(status="INPUT_ERROR", message=f"invalid json: {exc.msg}", exit_code=EXIT_BLOCKED)
    except AgentWorkValidationError as exc:
        return _safe_error_result(status="INPUT_ERROR", message=str(exc), exit_code=EXIT_BLOCKED)

    scope_decision = assess_agent_scope(request)
    approval_decision = approve_agent_work(
        scope_decision,
        human_approved=approve,
        approved_by=approved_by,
    )

    try:
        evidence_ref = write_agent_evidence(
            request=request,
            scope_decision=scope_decision,
            approval_decision=approval_decision,
            root_dir=evidence_root,
        )
    except (AgentEvidenceError, OSError) as exc:
        return AgentWorkCliResult(
            exit_code=EXIT_EVIDENCE_FAILED,
            status="EVIDENCE_WRITE_FAILED",
            message=str(exc),
            payload={
                "status": "EVIDENCE_WRITE_FAILED",
                "message": str(exc),
                "work_id": scope_decision.work_id,
                "scope_decision": scope_decision.to_dict(),
                "approval_decision": approval_decision.to_dict(),
                "read_only": True,
                "is_order_action": False,
                "broker_api_called": False,
                "live_mode_touched": False,
                "allowed_for_live_execution": False,
            },
        )

    if scope_decision.state == "BLOCKED":
        exit_code = EXIT_BLOCKED
        status = "BLOCKED"
        message = "agent work blocked by scope guard"
    elif not approval_decision.approved:
        exit_code = EXIT_REJECTED
        status = "REJECTED"
        message = "agent work rejected by approval layer"
    else:
        exit_code = EXIT_APPROVED
        status = "APPROVED_FOR_PATCH"
        message = "agent work approved for patch-only workflow"

    return AgentWorkCliResult(
        exit_code=exit_code,
        status=status,
        message=message,
        payload={
            "status": status,
            "message": message,
            "work_id": scope_decision.work_id,
            "scope_decision": scope_decision.to_dict(),
            "approval_decision": approval_decision.to_dict(),
            "evidence_ref": evidence_ref,
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
        },
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Submit a local agent work request safely.")
    parser.add_argument("--payload", required=True, help="Path to an AgentWorkRequest JSON payload.")
    parser.add_argument("--approve", action="store_true", help="Record explicit human approval for eligible patch work.")
    parser.add_argument("--approved-by", default=None, help="Reviewer/user name required when --approve is used for human-gated work.")
    parser.add_argument("--evidence-root", default="runtime/agent_work", help="Directory for local agent evidence files.")
    parser.add_argument("--json", action="store_true", help="Print full JSON result.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_agent_work_submission(
        payload_path=args.payload,
        approve=args.approve,
        approved_by=args.approved_by,
        evidence_root=args.evidence_root,
    )

    if args.json:
        print(json.dumps(result.payload, sort_keys=True, indent=2, default=str))
    else:
        print(f"{result.status}: {result.message}")
        if result.payload.get("work_id"):
            print(f"work_id={result.payload['work_id']}")

    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

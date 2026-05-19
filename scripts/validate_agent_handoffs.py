#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agent_system.handoff_validator import report_to_json, validate_handoff_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate role-based mini-agent handoff evidence for one task.")
    parser.add_argument("--task-id", required=True, help="Task ID prefix for docs/pr-handoffs files, for example AGENT-PR14.")
    parser.add_argument(
        "--handoff-dir",
        default="docs/pr-handoffs",
        help="Directory containing handoff markdown artifacts. Defaults to docs/pr-handoffs.",
    )
    parser.add_argument(
        "--required-role",
        action="append",
        dest="required_roles",
        help="Optional required role override. Repeat for multiple roles. Defaults to all required PR handoff roles.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    args = parser.parse_args()

    report = validate_handoff_evidence(
        task_id=args.task_id,
        handoff_dir=Path(args.handoff_dir),
        required_roles=args.required_roles,
    )

    if args.json:
        print(report_to_json(report))
    elif report.valid:
        print(f"handoff evidence valid: task_id={report.task_id} roles={','.join(report.roles_found)}")
    else:
        print(f"handoff evidence invalid: task_id={report.task_id}")
        for blocker in report.blockers:
            print(f"- {blocker}")
        for file_result in report.file_results:
            if not file_result.valid:
                print(f"- {file_result.path}: {file_result.error}")

    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

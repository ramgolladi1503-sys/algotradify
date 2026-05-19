#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_system.changed_file_auditor import audit_changed_files_against_handoffs


def _read_changed_files(args: argparse.Namespace) -> list[str]:
    changed_files: list[str] = []
    if args.changed_file:
        changed_files.extend(args.changed_file)
    if args.changed_files_file:
        file_path = Path(args.changed_files_file)
        changed_files.extend(
            line.strip()
            for line in file_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return changed_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit changed files against approved mini-agent handoff scope.")
    parser.add_argument("--task-id", required=True, help="Agent task id, for example AGENT-PR16.")
    parser.add_argument("--handoff-dir", default="docs/pr-handoffs", help="Directory containing handoff files.")
    parser.add_argument("--changed-file", action="append", help="Changed file path. Repeat for multiple files.")
    parser.add_argument("--changed-files-file", help="File containing one changed path per line.")
    parser.add_argument("--human-approved", action="store_true", help="Allow high-risk paths when already human approved.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    args = parser.parse_args()

    report = audit_changed_files_against_handoffs(
        task_id=args.task_id,
        changed_files=_read_changed_files(args),
        handoff_dir=Path(args.handoff_dir),
        human_approved=args.human_approved,
    )
    payload = report.to_dict()

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif report.valid:
        print(f"changed-file scope valid: task_id={report.task_id} files={len(report.changed_files)}")
    else:
        print(f"changed-file scope invalid: task_id={report.task_id}")
        for blocker in report.blockers:
            print(f"- {blocker}")
        for finding in report.findings:
            if not finding.accepted:
                print(f"- {finding.path}: {','.join(finding.blockers)}")

    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

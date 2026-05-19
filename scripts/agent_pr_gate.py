#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_system.pr_gate import load_changed_files, load_text_file, run_agent_pr_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local mini-agent PR developer gate.")
    parser.add_argument("--task-ref", required=True, help="Agent task reference, for example AGENT-PR17.")
    parser.add_argument("--handoff-dir", default="docs/pr-handoffs", help="Directory containing handoff files.")
    parser.add_argument("--pr-body-file", required=True, help="Path to a markdown PR body file.")
    parser.add_argument("--changed-file", action="append", help="Changed file path. Repeat for multiple files.")
    parser.add_argument("--changed-files-file", help="File containing one changed file path per line.")
    parser.add_argument("--human-approved", action="store_true", help="Allow high-risk paths when already human approved.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    args = parser.parse_args()

    changed_files: list[str] = []
    if args.changed_file:
        changed_files.extend(args.changed_file)
    if args.changed_files_file:
        changed_files.extend(load_changed_files(args.changed_files_file))

    report = run_agent_pr_gate(
        task_ref=args.task_ref,
        changed_files=changed_files,
        pr_body=load_text_file(args.pr_body_file),
        handoff_dir=Path(args.handoff_dir),
        human_approved=args.human_approved,
    )
    payload = report.to_dict()

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif report.valid:
        print(f"agent PR gate valid: task_id={report.task_id} changed_files={report.changed_file_count}")
    else:
        print(f"agent PR gate invalid: task_id={report.task_id}")
        for blocker in report.blockers:
            print(f"- {blocker}")

    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

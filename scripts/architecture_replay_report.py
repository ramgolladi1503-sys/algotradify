#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_system.architecture_replay import (
    architecture_replay_report_to_json,
    architecture_replay_report_to_markdown,
    run_architecture_replay_report,
)
from agent_system.pr_gate import load_changed_files, load_text_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic mini-agent architecture replay report.")
    parser.add_argument("--task-ref", required=True, help="Agent task reference, for example AGENT-PR18.")
    parser.add_argument("--handoff-dir", default="docs/pr-handoffs", help="Directory containing handoff files.")
    parser.add_argument("--pr-body-file", required=True, help="Path to PR body markdown.")
    parser.add_argument("--changed-file", action="append", help="Changed file path. Repeat for multiple files.")
    parser.add_argument("--changed-files-file", help="File containing one changed path per line.")
    parser.add_argument("--human-approved", action="store_true", help="Allow high-risk paths when already human approved.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    changed_files: list[str] = []
    if args.changed_file:
        changed_files.extend(args.changed_file)
    if args.changed_files_file:
        changed_files.extend(load_changed_files(args.changed_files_file))

    report = run_architecture_replay_report(
        task_ref=args.task_ref,
        changed_files=changed_files,
        pr_body=load_text_file(args.pr_body_file),
        handoff_dir=Path(args.handoff_dir),
        human_approved=args.human_approved,
    )

    if args.format == "markdown":
        print(architecture_replay_report_to_markdown(report))
    else:
        print(architecture_replay_report_to_json(report))

    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

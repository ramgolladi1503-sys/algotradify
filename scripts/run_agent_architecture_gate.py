#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_system.architecture_gate import run_agent_architecture_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the role-based mini-agent architecture gate.")
    parser.add_argument(
        "--task-ref",
        required=True,
        help="Agent task reference, for example AGENT-PR15, 'Agent PR 15', or a PR title containing Agent PR 15.",
    )
    parser.add_argument(
        "--handoff-dir",
        default="docs/pr-handoffs",
        help="Directory containing role handoff markdown artifacts.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full JSON gate report.")
    args = parser.parse_args()

    report = run_agent_architecture_gate(task_ref=args.task_ref, handoff_dir=Path(args.handoff_dir))
    payload = report.to_dict()

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif report.valid:
        print(f"agent architecture gate valid: task_id={report.task_id}")
    else:
        print(f"agent architecture gate invalid: task_id={report.task_id}")
        for blocker in report.blockers:
            print(f"- {blocker}")

    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

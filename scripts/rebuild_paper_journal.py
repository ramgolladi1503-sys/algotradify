#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paper_trading.rebuild import PaperJournalRebuildStatus, rebuild_paper_journal  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild deterministic paper state from the canonical paper event journal.",
    )
    parser.add_argument(
        "--journal",
        required=True,
        help="Path to the canonical paper event journal JSONL file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full rebuild result as JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = rebuild_paper_journal(args.journal)
    payload = result.to_dict()

    if args.json:
        print(json.dumps(payload, sort_keys=True, indent=2))
    else:
        print(
            "Paper journal rebuild: "
            f"status={payload['status']} "
            f"events={payload['event_count']} "
            f"ordered_events={payload['ordered_event_count']} "
            f"path={payload['journal_path']}"
        )
        if payload["blockers"]:
            print("Blockers:")
            for blocker in payload["blockers"]:
                print(f"- {blocker}")
        if payload["warnings"]:
            print("Warnings:")
            for warning in payload["warnings"]:
                print(f"- {warning}")

    return 2 if result.status == PaperJournalRebuildStatus.BLOCKED else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paper_trading.rebuild import rebuild_paper_journal  # noqa: E402
from paper_trading.reconciliation import PaperStateReconciliationStatus, reconcile_paper_state  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconcile deterministic rebuilt paper state against an observed paper state snapshot.",
    )
    parser.add_argument("--journal", required=True, help="Path to canonical paper event journal JSONL file.")
    parser.add_argument(
        "--observed-state",
        help="Optional path to an observed paper state JSON file. Missing value means reconcile against no observed state.",
    )
    parser.add_argument("--json", action="store_true", help="Print full reconciliation report as JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rebuild_result = rebuild_paper_journal(args.journal)
    observed_state = _load_observed_state(args.observed_state)
    report = reconcile_paper_state(rebuild_result, observed_state)
    payload = report.to_dict()

    if args.json:
        print(json.dumps(payload, sort_keys=True, indent=2))
    else:
        print(
            "Paper state reconciliation: "
            f"status={payload['status']} "
            f"matched={payload['matched']} "
            f"drifts={payload['drift_count']}"
        )
        if payload["blockers"]:
            print("Blockers:")
            for blocker in payload["blockers"]:
                print(f"- {blocker}")
        if payload["drifts"]:
            print("Drifts:")
            for drift in payload["drifts"]:
                print(f"- {drift['path']}: {drift['reason']}")
        if payload["warnings"]:
            print("Warnings:")
            for warning in payload["warnings"]:
                print(f"- {warning}")

    if report.status == PaperStateReconciliationStatus.BLOCKED:
        return 2
    if report.status == PaperStateReconciliationStatus.DRIFT:
        return 1
    return 0


def _load_observed_state(path: str | None) -> dict | None:
    if path is None:
        return None
    observed_path = Path(path)
    with observed_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and "state" in payload and isinstance(payload["state"], dict):
        return payload["state"]
    return payload if isinstance(payload, dict) else None


if __name__ == "__main__":
    raise SystemExit(main())

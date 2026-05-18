#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_SECTIONS = [
    "## Pre-code scope review",
    "## Post-code review",
    "## Test commands",
    "## Acceptance proof",
]

REQUIRED_PHRASES = [
    "Files to change",
    "Files not to touch",
    "Safety boundary",
    "Negative tests",
    "Regression risks",
    "Changed files match approved scope",
    "Forbidden files touched",
    "Safety boundary preserved",
]


def check_pr_body(body: str) -> list[str]:
    failures: list[str] = []
    for section in REQUIRED_SECTIONS:
        if section not in body:
            failures.append(f"missing required section: {section}")
    for phrase in REQUIRED_PHRASES:
        if phrase not in body:
            failures.append(f"missing required evidence phrase: {phrase}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PR body for required agent stage gate evidence.")
    parser.add_argument("body_file", help="Path to a file containing the PR body.")
    args = parser.parse_args()

    body_path = Path(args.body_file)
    if not body_path.exists():
        print(f"stage gate check failed: body file not found: {body_path}")
        return 2

    failures = check_pr_body(body_path.read_text(encoding="utf-8"))
    if failures:
        print("PR stage gate check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PR stage gate check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

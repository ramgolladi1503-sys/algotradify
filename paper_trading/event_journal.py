from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paper_trading.events import (
    PAPER_EVENT_SCHEMA_VERSION,
    PaperEvent,
    normalize_paper_event,
    paper_event_schema_contract,
    validate_paper_event,
)


@dataclass(frozen=True)
class PaperEventJournalResult:
    appended: bool
    event: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    path: str | None = None
    schema_version: str = PAPER_EVENT_SCHEMA_VERSION

    @property
    def paper_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    @property
    def broker_api_called(self) -> bool:
        return False

    @property
    def real_order_id(self) -> None:
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "journal_type": "CANONICAL_PAPER_EVENT_JOURNAL",
            "appended": self.appended,
            "event": dict(self.event) if self.event else None,
            "events": [dict(event) for event in self.events],
            "event_count": len(self.events),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "path": self.path,
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_event_journal_schema_contract() -> dict[str, Any]:
    contract = paper_event_schema_contract()
    return {
        **contract,
        "storage_format": "jsonl",
        "append_only": True,
        "load_blocks_on_corrupt_rows": True,
        "idempotency_behavior": {
            "duplicate_event_id": "blocked",
            "same_idempotency_key_same_event": "deterministic_noop",
            "same_idempotency_key_conflicting_event": "blocked",
        },
        "required_result_keys": [
            "schema_version",
            "journal_type",
            "appended",
            "event",
            "events",
            "event_count",
            "blockers",
            "warnings",
            "path",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
    }


def append_paper_event(path: str | Path, event: PaperEvent | dict[str, Any]) -> PaperEventJournalResult:
    normalized = normalize_paper_event(event)
    blockers = validate_paper_event(normalized)
    journal_path = Path(path)
    if blockers:
        return PaperEventJournalResult(appended=False, event=normalized, blockers=blockers, path=str(journal_path))

    existing_result = load_paper_events(journal_path)
    if existing_result.blockers:
        return PaperEventJournalResult(
            appended=False,
            event=normalized,
            events=existing_result.events,
            blockers=existing_result.blockers,
            path=str(journal_path),
        )

    duplicate_blockers = _duplicate_blockers(normalized, existing_result.events)
    if duplicate_blockers:
        idempotent_match = duplicate_blockers == ["PAPER_EVENT_DUPLICATE_IDEMPOTENCY_KEY_NOOP"]
        return PaperEventJournalResult(
            appended=False,
            event=normalized,
            events=existing_result.events,
            blockers=[] if idempotent_match else duplicate_blockers,
            warnings=duplicate_blockers if idempotent_match else [],
            path=str(journal_path),
        )

    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write(_stable_json(normalized))
        handle.write("\n")

    return PaperEventJournalResult(
        appended=True,
        event=normalized,
        events=[*existing_result.events, normalized],
        path=str(journal_path),
    )


def load_paper_events(path: str | Path) -> PaperEventJournalResult:
    journal_path = Path(path)
    if not journal_path.exists():
        return PaperEventJournalResult(appended=False, events=[], path=str(journal_path))

    events: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    seen_idempotency: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []

    with journal_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError:
                blockers.append(f"PAPER_EVENT_JOURNAL_CORRUPT_JSONL_LINE_{line_number}")
                continue
            normalized = normalize_paper_event(decoded)
            event_blockers = validate_paper_event(normalized)
            if event_blockers:
                blockers.extend(f"LINE_{line_number}_{blocker}" for blocker in event_blockers)
                continue
            event_id = str(normalized["event_id"])
            idempotency_key = str(normalized["idempotency_key"])
            if event_id in seen_event_ids:
                blockers.append(f"LINE_{line_number}_PAPER_EVENT_DUPLICATE_EVENT_ID")
                continue
            if idempotency_key in seen_idempotency and _stable_json(seen_idempotency[idempotency_key]) != _stable_json(normalized):
                blockers.append(f"LINE_{line_number}_PAPER_EVENT_CONFLICTING_IDEMPOTENCY_KEY")
                continue
            seen_event_ids.add(event_id)
            seen_idempotency[idempotency_key] = normalized
            events.append(normalized)

    return PaperEventJournalResult(appended=False, events=events, blockers=blockers, path=str(journal_path))


def _duplicate_blockers(event: dict[str, Any], existing_events: list[dict[str, Any]]) -> list[str]:
    incoming_event_id = str(event["event_id"])
    incoming_idempotency_key = str(event["idempotency_key"])
    incoming_json = _stable_json(event)
    for existing in existing_events:
        if str(existing["event_id"]) == incoming_event_id:
            return ["PAPER_EVENT_DUPLICATE_EVENT_ID"]
        if str(existing["idempotency_key"]) == incoming_idempotency_key:
            if _stable_json(existing) == incoming_json:
                return ["PAPER_EVENT_DUPLICATE_IDEMPOTENCY_KEY_NOOP"]
            return ["PAPER_EVENT_CONFLICTING_IDEMPOTENCY_KEY"]
    return []


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

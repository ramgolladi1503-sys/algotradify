from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from paper_trading.event_journal import load_paper_events, paper_event_journal_schema_contract
from paper_trading.event_ordering import guard_paper_event_ordering, paper_event_ordering_guard_schema_contract
from paper_trading.state_reducer import paper_state_reducer_schema_contract, reduce_paper_events


PAPER_JOURNAL_REBUILD_SCHEMA_VERSION = "1.0"


class PaperJournalRebuildStatus(StrEnum):
    REBUILT = "REBUILT"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperJournalRebuildResult:
    rebuilt: bool
    status: PaperJournalRebuildStatus
    journal_path: str | None = None
    event_count: int = 0
    ordered_event_count: int = 0
    state: dict[str, Any] = field(default_factory=dict)
    journal: dict[str, Any] = field(default_factory=dict)
    ordering: dict[str, Any] = field(default_factory=dict)
    reducer: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_JOURNAL_REBUILD_SCHEMA_VERSION

    @property
    def paper_only(self) -> bool:
        return True

    @property
    def read_only(self) -> bool:
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
            "rebuild_type": "PAPER_STATE_REBUILD_CLI",
            "status": self.status.value,
            "rebuilt": self.rebuilt,
            "journal_path": self.journal_path,
            "event_count": self.event_count,
            "ordered_event_count": self.ordered_event_count,
            "state": deepcopy(self.state),
            "journal": deepcopy(self.journal),
            "ordering": deepcopy(self.ordering),
            "reducer": deepcopy(self.reducer),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_journal_rebuild_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_JOURNAL_REBUILD_SCHEMA_VERSION,
        "rebuild_type": "PAPER_STATE_REBUILD_CLI",
        "consumes": [
            "CANONICAL_PAPER_EVENT_JOURNAL",
            "PAPER_EVENT_ORDERING_IDEMPOTENCY_GUARD",
            "DETERMINISTIC_PAPER_STATE_REDUCER",
        ],
        "statuses": [status.value for status in PaperJournalRebuildStatus],
        "required_result_keys": [
            "schema_version",
            "rebuild_type",
            "status",
            "rebuilt",
            "journal_path",
            "event_count",
            "ordered_event_count",
            "state",
            "journal",
            "ordering",
            "reducer",
            "blockers",
            "warnings",
            "paper_only",
            "read_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "safe_flags": {
            "paper_only": True,
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
        "pipeline": ["load_paper_events", "guard_paper_event_ordering", "reduce_paper_events"],
        "upstream_contracts": {
            "journal": paper_event_journal_schema_contract(),
            "ordering": paper_event_ordering_guard_schema_contract(),
            "reducer": paper_state_reducer_schema_contract(),
        },
        "cli_exit_codes": {"REBUILT": 0, "EMPTY": 0, "BLOCKED": 2},
        "scope_boundary": [
            "read_only_rebuild_only",
            "no_journal_append",
            "no_state_export",
            "no_api",
            "no_ui",
            "no_runtime_wiring",
        ],
    }


def rebuild_paper_journal(path: str | Path | None) -> PaperJournalRebuildResult:
    blockers = validate_paper_journal_rebuild_inputs(path)
    journal_path = _normalize_path(path)
    if blockers:
        return PaperJournalRebuildResult(
            rebuilt=False,
            status=PaperJournalRebuildStatus.BLOCKED,
            journal_path=journal_path,
            blockers=blockers,
        )

    journal_result = load_paper_events(journal_path or "")
    journal_payload = journal_result.to_dict()
    if journal_result.blockers:
        return PaperJournalRebuildResult(
            rebuilt=False,
            status=PaperJournalRebuildStatus.BLOCKED,
            journal_path=journal_path,
            event_count=len(journal_result.events),
            journal=journal_payload,
            blockers=_prefixed("JOURNAL", journal_result.blockers),
            warnings=list(journal_result.warnings),
        )

    ordering_result = guard_paper_event_ordering(journal_result.events)
    ordering_payload = ordering_result.to_dict()
    if ordering_result.blockers:
        return PaperJournalRebuildResult(
            rebuilt=False,
            status=PaperJournalRebuildStatus.BLOCKED,
            journal_path=journal_path,
            event_count=len(journal_result.events),
            ordered_event_count=len(ordering_result.ordered_events),
            journal=journal_payload,
            ordering=ordering_payload,
            blockers=_prefixed("ORDERING", ordering_result.blockers),
            warnings=[*journal_result.warnings, *ordering_result.warnings],
        )

    reducer_result = reduce_paper_events(ordering_result.ordered_events)
    reducer_payload = reducer_result.to_dict()
    if reducer_result.blockers:
        return PaperJournalRebuildResult(
            rebuilt=False,
            status=PaperJournalRebuildStatus.BLOCKED,
            journal_path=journal_path,
            event_count=len(journal_result.events),
            ordered_event_count=len(ordering_result.ordered_events),
            journal=journal_payload,
            ordering=ordering_payload,
            reducer=reducer_payload,
            blockers=_prefixed("REDUCER", reducer_result.blockers),
            warnings=[*journal_result.warnings, *ordering_result.warnings, *reducer_result.warnings],
        )

    status = PaperJournalRebuildStatus.EMPTY if len(ordering_result.ordered_events) == 0 else PaperJournalRebuildStatus.REBUILT
    return PaperJournalRebuildResult(
        rebuilt=True,
        status=status,
        journal_path=journal_path,
        event_count=len(journal_result.events),
        ordered_event_count=len(ordering_result.ordered_events),
        state=reducer_result.state,
        journal=journal_payload,
        ordering=ordering_payload,
        reducer=reducer_payload,
        warnings=_dedupe([*journal_result.warnings, *ordering_result.warnings, *reducer_result.warnings]),
    )


def validate_paper_journal_rebuild_inputs(path: str | Path | None) -> list[str]:
    if path is None:
        return ["PAPER_JOURNAL_REBUILD_PATH_REQUIRED"]
    if isinstance(path, Path):
        normalized = str(path)
    elif isinstance(path, str):
        normalized = path.strip()
    else:
        return ["PAPER_JOURNAL_REBUILD_PATH_MUST_BE_STRING_OR_PATH"]
    if not normalized:
        return ["PAPER_JOURNAL_REBUILD_PATH_REQUIRED"]
    return []


def _normalize_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    if isinstance(path, Path):
        return str(path)
    if isinstance(path, str):
        return path.strip() or None
    return None


def _prefixed(source: str, blockers: list[str]) -> list[str]:
    return [f"PAPER_JOURNAL_REBUILD_{source}_{blocker}" for blocker in blockers]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

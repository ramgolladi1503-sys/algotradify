from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from paper_trading.events import PAPER_EVENT_SCHEMA_VERSION, normalize_paper_event, validate_paper_event


PAPER_EVENT_ORDERING_SCHEMA_VERSION = "1.0"


class PaperEventOrderingGuardStatus(StrEnum):
    VALID = "VALID"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperEventOrderingGuardResult:
    valid: bool
    status: PaperEventOrderingGuardStatus
    ordered_events: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cycles: dict[str, dict[str, Any]] = field(default_factory=dict)
    schema_version: str = PAPER_EVENT_ORDERING_SCHEMA_VERSION

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
            "guard_type": "PAPER_EVENT_ORDERING_IDEMPOTENCY_GUARD",
            "valid": self.valid,
            "status": self.status.value,
            "ordered_events": [dict(event) for event in self.ordered_events],
            "event_count": len(self.ordered_events),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "cycles": {cycle_id: dict(summary) for cycle_id, summary in self.cycles.items()},
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_event_ordering_guard_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_EVENT_ORDERING_SCHEMA_VERSION,
        "guard_type": "PAPER_EVENT_ORDERING_IDEMPOTENCY_GUARD",
        "consumes": ["CANONICAL_PAPER_EVENT_JOURNAL"],
        "event_schema_version": PAPER_EVENT_SCHEMA_VERSION,
        "statuses": [status.value for status in PaperEventOrderingGuardStatus],
        "required_result_keys": [
            "schema_version",
            "guard_type",
            "valid",
            "status",
            "ordered_events",
            "event_count",
            "blockers",
            "warnings",
            "cycles",
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
        "ordering_rules": {
            "repair_or_sort_events": False,
            "per_cycle_event_sequence": "strictly_contiguous_in_input_order",
            "per_cycle_ts_epoch": "non_decreasing_in_input_order",
            "duplicate_event_id": "blocked",
            "duplicate_idempotency_key": "blocked",
            "invalid_canonical_event": "blocked",
        },
        "scope_boundary": [
            "read_only_guard_only",
            "no_reducer_mutation",
            "no_file_io",
            "no_broker_execution",
            "no_live_orders",
            "no_api",
            "no_ui",
            "no_runtime_wiring",
        ],
    }


def guard_paper_event_ordering(
    events: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
) -> PaperEventOrderingGuardResult:
    blockers, normalized_events, cycles = validate_paper_event_ordering_inputs(events)
    if blockers:
        return PaperEventOrderingGuardResult(
            valid=False,
            status=PaperEventOrderingGuardStatus.BLOCKED,
            ordered_events=[],
            blockers=blockers,
            cycles=cycles,
        )
    if not normalized_events:
        return PaperEventOrderingGuardResult(
            valid=True,
            status=PaperEventOrderingGuardStatus.EMPTY,
            ordered_events=[],
            warnings=["PAPER_EVENT_ORDERING_EMPTY_EVENT_LIST"],
            cycles={},
        )
    return PaperEventOrderingGuardResult(
        valid=True,
        status=PaperEventOrderingGuardStatus.VALID,
        ordered_events=normalized_events,
        cycles=cycles,
    )


def validate_paper_event_ordering_inputs(
    events: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
) -> tuple[list[str], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if events is None:
        return ["PAPER_EVENT_ORDERING_EVENTS_REQUIRED"], [], {}
    if not isinstance(events, (list, tuple)):
        return ["PAPER_EVENT_ORDERING_EVENTS_MUST_BE_LIST"], [], {}

    blockers: list[str] = []
    normalized_events: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    seen_idempotency_keys: set[str] = set()
    cycle_state: dict[str, dict[str, Any]] = {}

    for index, raw_event in enumerate(events):
        try:
            event = normalize_paper_event(raw_event)
        except (TypeError, ValueError):
            blockers.append(f"EVENT_{index}_PAPER_EVENT_NOT_OBJECT")
            continue

        event_blockers = validate_paper_event(event)
        if event_blockers:
            blockers.extend(f"EVENT_{index}_{blocker}" for blocker in event_blockers)
            continue

        event_id = str(event["event_id"])
        idempotency_key = str(event["idempotency_key"])
        cycle_id = str(event["cycle_id"])
        event_sequence = int(event["event_sequence"])
        ts_epoch = float(event["ts_epoch"])

        if event_id in seen_event_ids:
            blockers.append(f"EVENT_{index}_PAPER_EVENT_ORDERING_DUPLICATE_EVENT_ID")
        if idempotency_key in seen_idempotency_keys:
            blockers.append(f"EVENT_{index}_PAPER_EVENT_ORDERING_DUPLICATE_IDEMPOTENCY_KEY")

        cycle = cycle_state.setdefault(
            cycle_id,
            {
                "cycle_id": cycle_id,
                "event_count": 0,
                "first_event_id": event_id,
                "last_event_id": None,
                "first_sequence": event_sequence,
                "last_sequence": None,
                "first_ts_epoch": ts_epoch,
                "last_ts_epoch": None,
                "paper_only": True,
                "read_only": True,
                "is_order_action": False,
                "broker_api_called": False,
                "real_order_id": None,
            },
        )

        previous_sequence = cycle.get("last_sequence")
        previous_ts_epoch = cycle.get("last_ts_epoch")
        if previous_sequence is not None:
            expected_sequence = int(previous_sequence) + 1
            if event_sequence != expected_sequence:
                blockers.append(
                    f"EVENT_{index}_PAPER_EVENT_SEQUENCE_GAP_OR_REGRESSION:{cycle_id}:{previous_sequence}->{event_sequence}"
                )
        elif event_sequence != 1:
            blockers.append(f"EVENT_{index}_PAPER_EVENT_SEQUENCE_MUST_START_AT_1:{cycle_id}:{event_sequence}")

        if previous_ts_epoch is not None and ts_epoch < float(previous_ts_epoch):
            blockers.append(f"EVENT_{index}_PAPER_EVENT_TS_EPOCH_REGRESSION:{cycle_id}:{previous_ts_epoch}->{ts_epoch}")

        cycle["event_count"] = int(cycle["event_count"]) + 1
        cycle["last_event_id"] = event_id
        cycle["last_sequence"] = event_sequence
        cycle["last_ts_epoch"] = ts_epoch
        seen_event_ids.add(event_id)
        seen_idempotency_keys.add(idempotency_key)
        normalized_events.append(event)

    cycles = {cycle_id: dict(summary) for cycle_id, summary in sorted(cycle_state.items())}
    return _dedupe(blockers), normalized_events if not blockers else [], cycles


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

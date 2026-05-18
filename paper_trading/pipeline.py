from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any

from paper_trading.event_ordering import guard_paper_event_ordering, paper_event_ordering_guard_schema_contract
from paper_trading.events import PAPER_EVENT_SCHEMA_VERSION, validate_paper_event
from paper_trading.fill_simulation import paper_fill_simulation_schema_contract, simulate_paper_fill
from paper_trading.intent_bridge import build_paper_order_intent, paper_order_intent_schema_contract
from paper_trading.lifecycle import build_paper_order_lifecycle_event, paper_order_lifecycle_schema_contract
from paper_trading.state_reducer import paper_state_reducer_schema_contract, reduce_paper_events


PAPER_TRADING_PIPELINE_SCHEMA_VERSION = "1.0"


class PaperTradingPipelineStatus(StrEnum):
    COMPLETED = "COMPLETED"
    NOOP = "NOOP"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperTradingPipelineResult:
    completed: bool
    status: PaperTradingPipelineStatus
    cycle_id: str | None = None
    candidate_id: str | None = None
    strategy_id: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    stages: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_TRADING_PIPELINE_SCHEMA_VERSION

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
            "pipeline_type": "IN_MEMORY_PAPER_TRADING_PIPELINE",
            "completed": self.completed,
            "status": self.status.value,
            "cycle_id": self.cycle_id,
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "event_count": len(self.events),
            "events": deepcopy(self.events),
            "state": deepcopy(self.state),
            "stages": deepcopy(self.stages),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_trading_pipeline_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_TRADING_PIPELINE_SCHEMA_VERSION,
        "pipeline_type": "IN_MEMORY_PAPER_TRADING_PIPELINE",
        "statuses": [status.value for status in PaperTradingPipelineStatus],
        "consumes": [
            "PAPER_ORDER_INTENT_BRIDGE",
            "PAPER_ORDER_LIFECYCLE",
            "PAPER_FILL_SIMULATION_ENGINE",
            "PAPER_EVENT_ORDERING_IDEMPOTENCY_GUARD",
            "DETERMINISTIC_PAPER_STATE_REDUCER",
        ],
        "required_result_keys": [
            "schema_version",
            "pipeline_type",
            "completed",
            "status",
            "cycle_id",
            "candidate_id",
            "strategy_id",
            "event_count",
            "events",
            "state",
            "stages",
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
        "scope_boundary": [
            "in_memory_only",
            "no_journal_append",
            "no_persistence_layer",
            "no_api",
            "no_ui",
            "no_runtime_wiring",
            "no_broker_execution",
            "no_live_orders",
        ],
        "upstream_contracts": {
            "intent": paper_order_intent_schema_contract(),
            "lifecycle": paper_order_lifecycle_schema_contract(),
            "fill": paper_fill_simulation_schema_contract(),
            "ordering": paper_event_ordering_guard_schema_contract(),
            "reducer": paper_state_reducer_schema_contract(),
        },
    }


def run_paper_trading_pipeline(
    *,
    cycle_id: str | None,
    top_executable: dict[str, Any] | None,
    execution_safety: dict[str, Any] | None,
    quote: dict[str, Any] | None,
    readiness: dict[str, Any] | None = None,
    market_data: dict[str, Any] | None = None,
    instrument_health: dict[str, Any] | None = None,
    ts_epoch: float | None = None,
    now_epoch: float | None = None,
    max_quote_age_sec: float = 5.0,
) -> PaperTradingPipelineResult:
    input_blockers = validate_paper_trading_pipeline_inputs(
        cycle_id=cycle_id,
        top_executable=top_executable,
        execution_safety=execution_safety,
        quote=quote,
        readiness=readiness,
        market_data=market_data,
        instrument_health=instrument_health,
    )
    candidate_id = _candidate_id(top_executable)
    strategy_id = _strategy_id(top_executable)
    if input_blockers:
        return PaperTradingPipelineResult(
            completed=False,
            status=PaperTradingPipelineStatus.BLOCKED,
            cycle_id=_str_or_none(cycle_id),
            candidate_id=candidate_id,
            strategy_id=strategy_id,
            blockers=input_blockers,
        )

    stages: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    warnings: list[str] = []

    intent_result = build_paper_order_intent(
        top_executable=top_executable,
        execution_safety=execution_safety,
        readiness=readiness,
        market_data=market_data,
        instrument_health=instrument_health,
        ts_epoch=ts_epoch,
    )
    intent_payload = intent_result.to_dict()
    stages["intent"] = intent_payload
    warnings.extend(intent_payload.get("warnings") or [])
    if not intent_result.created or not intent_payload.get("intent"):
        return _blocked_result(
            cycle_id=cycle_id,
            candidate_id=candidate_id,
            strategy_id=strategy_id,
            stages=stages,
            blockers=_prefixed("INTENT", intent_payload.get("blockers") or ["PAPER_PIPELINE_INTENT_NOT_CREATED"]),
            warnings=warnings,
        )

    intent = intent_payload["intent"]
    candidate_id = str(intent.get("candidate_id") or candidate_id or "")
    strategy_id = _str_or_none(intent.get("strategy") or strategy_id)
    events.append(_canonical_event(cycle_id=str(cycle_id), sequence=1, event_type="PAPER_ORDER_INTENT_CREATED", payload=intent, intent=intent, ts_epoch=ts_epoch))

    created = build_paper_order_lifecycle_event(intent=intent, requested_status="CREATED", ts_epoch=_ts(ts_epoch, 1))
    created_payload = created.to_dict()
    stages["lifecycle_created"] = created_payload
    warnings.extend(created_payload.get("warnings") or [])
    if not created.created or not created_payload.get("event"):
        return _blocked_result(cycle_id=cycle_id, candidate_id=candidate_id, strategy_id=strategy_id, events=events, stages=stages, blockers=_prefixed("LIFECYCLE_CREATED", created_payload.get("blockers") or ["PAPER_PIPELINE_CREATED_EVENT_NOT_CREATED"]), warnings=warnings)

    accepted = build_paper_order_lifecycle_event(intent=intent, previous_event=created_payload["event"], requested_status="ACCEPTED", ts_epoch=_ts(ts_epoch, 2))
    accepted_payload = accepted.to_dict()
    stages["lifecycle_accepted"] = accepted_payload
    warnings.extend(accepted_payload.get("warnings") or [])
    if not accepted.created or not accepted_payload.get("event"):
        return _blocked_result(cycle_id=cycle_id, candidate_id=candidate_id, strategy_id=strategy_id, events=events, stages=stages, blockers=_prefixed("LIFECYCLE_ACCEPTED", accepted_payload.get("blockers") or ["PAPER_PIPELINE_ACCEPTED_EVENT_NOT_CREATED"]), warnings=warnings)
    events.append(_canonical_event(cycle_id=str(cycle_id), sequence=2, event_type="PAPER_ORDER_ACCEPTED", payload=accepted_payload["event"], intent=intent, lifecycle=accepted_payload["event"], ts_epoch=_ts(ts_epoch, 2)))

    opened = build_paper_order_lifecycle_event(intent=intent, previous_event=accepted_payload["event"], requested_status="OPEN", ts_epoch=_ts(ts_epoch, 3))
    opened_payload = opened.to_dict()
    stages["lifecycle_opened"] = opened_payload
    warnings.extend(opened_payload.get("warnings") or [])
    if not opened.created or not opened_payload.get("event"):
        return _blocked_result(cycle_id=cycle_id, candidate_id=candidate_id, strategy_id=strategy_id, events=events, stages=stages, blockers=_prefixed("LIFECYCLE_OPENED", opened_payload.get("blockers") or ["PAPER_PIPELINE_OPEN_EVENT_NOT_CREATED"]), warnings=warnings)
    events.append(_canonical_event(cycle_id=str(cycle_id), sequence=3, event_type="PAPER_ORDER_OPENED", payload=opened_payload["event"], intent=intent, lifecycle=opened_payload["event"], ts_epoch=_ts(ts_epoch, 3)))

    fill = simulate_paper_fill(
        intent=intent,
        previous_event=opened_payload["event"],
        quote=quote,
        ts_epoch=_ts(ts_epoch, 4),
        now_epoch=now_epoch,
        max_quote_age_sec=max_quote_age_sec,
    )
    fill_payload = fill.to_dict()
    stages["fill"] = fill_payload
    warnings.extend(fill_payload.get("warnings") or [])
    if fill_payload.get("status") == "BLOCKED":
        return _blocked_result(cycle_id=cycle_id, candidate_id=candidate_id, strategy_id=strategy_id, events=events, stages=stages, blockers=_prefixed("FILL", fill_payload.get("blockers") or ["PAPER_PIPELINE_FILL_BLOCKED"]), warnings=warnings)

    fill_lifecycle = fill_payload.get("lifecycle_event")
    if isinstance(fill_lifecycle, dict):
        event_type = _canonical_fill_event_type(fill_lifecycle.get("status"))
        events.append(
            _canonical_event(
                cycle_id=str(cycle_id),
                sequence=4,
                event_type=event_type,
                payload={**fill_payload, "lifecycle_event": fill_lifecycle},
                intent=intent,
                lifecycle=fill_lifecycle,
                ts_epoch=_ts(ts_epoch, 4),
            )
        )

    event_blockers = _validate_canonical_events(events)
    if event_blockers:
        return _blocked_result(cycle_id=cycle_id, candidate_id=candidate_id, strategy_id=strategy_id, events=events, stages=stages, blockers=_prefixed("CANONICAL_EVENT", event_blockers), warnings=warnings)

    ordering = guard_paper_event_ordering(events)
    ordering_payload = ordering.to_dict()
    stages["ordering"] = ordering_payload
    warnings.extend(ordering_payload.get("warnings") or [])
    if ordering_payload.get("status") == "BLOCKED":
        return _blocked_result(cycle_id=cycle_id, candidate_id=candidate_id, strategy_id=strategy_id, events=events, stages=stages, blockers=_prefixed("ORDERING", ordering_payload.get("blockers") or ["PAPER_PIPELINE_ORDERING_BLOCKED"]), warnings=warnings)

    reducer = reduce_paper_events(ordering_payload.get("ordered_events") or [])
    reducer_payload = reducer.to_dict()
    stages["reducer"] = reducer_payload
    warnings.extend(reducer_payload.get("warnings") or [])
    if reducer_payload.get("status") == "BLOCKED":
        return _blocked_result(cycle_id=cycle_id, candidate_id=candidate_id, strategy_id=strategy_id, events=events, stages=stages, blockers=_prefixed("REDUCER", reducer_payload.get("blockers") or ["PAPER_PIPELINE_REDUCER_BLOCKED"]), warnings=warnings)

    return PaperTradingPipelineResult(
        completed=True,
        status=PaperTradingPipelineStatus.COMPLETED,
        cycle_id=str(cycle_id),
        candidate_id=candidate_id,
        strategy_id=strategy_id,
        events=events,
        state=reducer_payload.get("state") or {},
        stages=stages,
        warnings=_dedupe(warnings),
    )


def validate_paper_trading_pipeline_inputs(
    *,
    cycle_id: str | None,
    top_executable: dict[str, Any] | None,
    execution_safety: dict[str, Any] | None,
    quote: dict[str, Any] | None,
    readiness: dict[str, Any] | None = None,
    market_data: dict[str, Any] | None = None,
    instrument_health: dict[str, Any] | None = None,
) -> list[str]:
    blockers: list[str] = []
    if not _str_or_none(cycle_id):
        blockers.append("PAPER_PIPELINE_CYCLE_ID_REQUIRED")
    if not isinstance(top_executable, dict):
        blockers.append("PAPER_PIPELINE_TOP_EXECUTABLE_REQUIRED")
    if not isinstance(execution_safety, dict):
        blockers.append("PAPER_PIPELINE_EXECUTION_SAFETY_REQUIRED")
    if not isinstance(quote, dict):
        blockers.append("PAPER_PIPELINE_CONTROLLED_QUOTE_REQUIRED")

    blockers.extend(_unsafe_payload_blockers("TOP_EXECUTABLE", top_executable))
    blockers.extend(_unsafe_payload_blockers("EXECUTION_SAFETY", execution_safety))
    blockers.extend(_unsafe_payload_blockers("QUOTE", quote))
    blockers.extend(_unsafe_payload_blockers("READINESS", readiness))
    blockers.extend(_unsafe_payload_blockers("MARKET_DATA", market_data))
    blockers.extend(_unsafe_payload_blockers("INSTRUMENT_HEALTH", instrument_health))
    return _dedupe(blockers)


def _canonical_event(
    *,
    cycle_id: str,
    sequence: int,
    event_type: str,
    payload: dict[str, Any],
    intent: dict[str, Any],
    ts_epoch: float | None,
    lifecycle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lifecycle_payload = lifecycle or {}
    paper_order_id = _str_or_none(lifecycle_payload.get("paper_order_id") or intent.get("paper_order_id"))
    seed = f"{cycle_id}|{sequence}|{event_type}|{intent.get('paper_order_intent_id')}|{paper_order_id or ''}"
    event_id = f"paper-pipeline-{sha256(seed.encode('utf-8')).hexdigest()[:16]}"
    return {
        "schema_version": PAPER_EVENT_SCHEMA_VERSION,
        "event_id": event_id,
        "cycle_id": cycle_id,
        "event_sequence": sequence,
        "candidate_id": _str_or_none(intent.get("candidate_id")),
        "strategy_id": _str_or_none(intent.get("strategy")),
        "paper_order_intent_id": _str_or_none(intent.get("paper_order_intent_id")),
        "paper_order_id": paper_order_id,
        "event_type": event_type,
        "ts_epoch": _ts(ts_epoch, sequence),
        "idempotency_key": f"{cycle_id}:{sequence}:{event_type}:{intent.get('paper_order_intent_id')}",
        "payload": deepcopy(payload),
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _canonical_fill_event_type(status: Any) -> str:
    normalized = str(status or "").upper()
    if normalized == "FILLED":
        return "PAPER_ORDER_FILLED"
    if normalized == "PARTIALLY_FILLED":
        return "PAPER_ORDER_PARTIALLY_FILLED"
    if normalized == "REJECTED":
        return "PAPER_ORDER_REJECTED"
    if normalized == "EXPIRED":
        return "PAPER_ORDER_EXPIRED"
    if normalized == "CANCELLED":
        return "PAPER_ORDER_CANCELLED"
    return "PAPER_ORDER_OPENED"


def _validate_canonical_events(events: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for index, event in enumerate(events):
        event_blockers = validate_paper_event(event)
        blockers.extend(f"EVENT_{index}_{blocker}" for blocker in event_blockers)
    return _dedupe(blockers)


def _blocked_result(
    *,
    cycle_id: str | None,
    candidate_id: str | None,
    strategy_id: str | None,
    blockers: list[str],
    warnings: list[str],
    events: list[dict[str, Any]] | None = None,
    stages: dict[str, Any] | None = None,
) -> PaperTradingPipelineResult:
    return PaperTradingPipelineResult(
        completed=False,
        status=PaperTradingPipelineStatus.BLOCKED,
        cycle_id=_str_or_none(cycle_id),
        candidate_id=candidate_id,
        strategy_id=strategy_id,
        events=events or [],
        stages=stages or {},
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
    )


def _unsafe_payload_blockers(name: str, payload: Any) -> list[str]:
    if payload is None:
        return []
    if not isinstance(payload, dict):
        return [f"PAPER_PIPELINE_{name}_MUST_BE_OBJECT"]
    blockers: list[str] = []
    for path, key, value in _walk_dict(payload):
        if key == "paper_only" and value is not True:
            blockers.append(f"PAPER_PIPELINE_{name}_{path}_UNSAFE_PAPER_ONLY_FLAG")
        if key == "is_order_action" and value is not False:
            blockers.append(f"PAPER_PIPELINE_{name}_{path}_UNSAFE_ORDER_ACTION_FLAG")
        if key == "broker_api_called" and value is True:
            blockers.append(f"PAPER_PIPELINE_{name}_{path}_BROKER_API_CALLED")
        if key == "real_order_id" and value not in (None, ""):
            blockers.append(f"PAPER_PIPELINE_{name}_{path}_REAL_ORDER_ID_PRESENT")
    return blockers


def _walk_dict(payload: dict[str, Any], prefix: str = "ROOT"):
    for key, value in payload.items():
        path = f"{prefix}_{str(key).upper()}"
        yield path, str(key), value
        if isinstance(value, dict):
            yield from _walk_dict(value, prefix=path)


def _candidate_id(top_executable: dict[str, Any] | None) -> str | None:
    if not isinstance(top_executable, dict):
        return None
    selected = top_executable.get("selected")
    if not isinstance(selected, dict):
        return None
    return _str_or_none(selected.get("candidate_id"))


def _strategy_id(top_executable: dict[str, Any] | None) -> str | None:
    if not isinstance(top_executable, dict):
        return None
    selected = top_executable.get("selected")
    if not isinstance(selected, dict):
        return None
    return _str_or_none(selected.get("strategy") or selected.get("strategy_id") or selected.get("setup_family"))


def _str_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _ts(base: float | None, offset: int) -> float | None:
    if base is None:
        return None
    try:
        return float(base) + (float(offset) * 0.001)
    except (TypeError, ValueError):
        return None


def _prefixed(source: str, blockers: list[str]) -> list[str]:
    return [f"PAPER_PIPELINE_{source}_{blocker}" for blocker in blockers]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

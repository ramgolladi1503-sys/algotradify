from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from paper_trading.persistence import load_paper_evidence_records, write_paper_evidence_record
from paper_trading.pipeline import paper_trading_pipeline_schema_contract, run_paper_trading_pipeline
from paper_trading.session_boundary import (
    PAPER_SESSION_BOUNDARY_RECORD_TYPE,
    build_paper_session_id,
    mark_paper_session_boundary,
    paper_session_boundary_schema_contract,
)


PAPER_SCENARIO_SCHEMA_VERSION = "1.0"


class PaperScenarioStatus(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class PaperScenarioName(StrEnum):
    FULL_FILL_HAPPY_PATH = "FULL_FILL_HAPPY_PATH"
    PARTIAL_FILL_PATH = "PARTIAL_FILL_PATH"
    NO_FILL_PATH = "NO_FILL_PATH"
    STALE_QUOTE_BLOCKED_PATH = "STALE_QUOTE_BLOCKED_PATH"
    SESSION_RESET_MARKER_PATH = "SESSION_RESET_MARKER_PATH"


@dataclass(frozen=True)
class PaperScenarioResult:
    scenario_name: str | None
    status: PaperScenarioStatus
    passed: bool = False
    session_id: str | None = None
    evidence_path: str | None = None
    expected: dict[str, Any] = field(default_factory=dict)
    actual: dict[str, Any] = field(default_factory=dict)
    pipeline: dict[str, Any] = field(default_factory=dict)
    session_boundaries: dict[str, Any] = field(default_factory=dict)
    persistence: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_SCENARIO_SCHEMA_VERSION

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
            "scenario_result_type": "PAPER_SCENARIO_RESULT",
            "scenario_name": self.scenario_name,
            "status": self.status.value,
            "passed": self.passed,
            "session_id": self.session_id,
            "evidence_path": self.evidence_path,
            "expected": deepcopy(self.expected),
            "actual": deepcopy(self.actual),
            "pipeline": deepcopy(self.pipeline),
            "session_boundaries": deepcopy(self.session_boundaries),
            "persistence": deepcopy(self.persistence),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_scenario_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_SCENARIO_SCHEMA_VERSION,
        "scenario_result_type": "PAPER_SCENARIO_RESULT",
        "statuses": [status.value for status in PaperScenarioStatus],
        "scenario_names": [name.value for name in PaperScenarioName],
        "required_result_keys": [
            "schema_version",
            "scenario_result_type",
            "scenario_name",
            "status",
            "passed",
            "session_id",
            "evidence_path",
            "expected",
            "actual",
            "pipeline",
            "session_boundaries",
            "persistence",
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
            "deterministic_test_scenarios_only",
            "no_runtime_wiring",
            "no_api",
            "no_ui",
            "no_broker_execution",
            "no_live_orders",
            "no_strategy_work",
            "no_export_bundle",
            "no_replay_dataset",
            "no_expectancy_scoring",
        ],
        "upstream_contracts": {
            "pipeline": paper_trading_pipeline_schema_contract(),
            "session_boundary": paper_session_boundary_schema_contract(),
        },
    }


def run_standard_paper_scenarios(
    *,
    evidence_dir: str | Path | None,
    trading_date: str = "2026-05-18",
) -> dict[str, Any]:
    if evidence_dir is None:
        return _suite_result([], ["PAPER_SCENARIO_EVIDENCE_DIR_REQUIRED"])
    base = Path(evidence_dir)
    results: list[dict[str, Any]] = []
    blockers: list[str] = []
    for scenario_name in PaperScenarioName:
        scenario_path = base / f"{scenario_name.value.lower()}.jsonl"
        result = run_paper_scenario(
            scenario_name=scenario_name.value,
            evidence_path=scenario_path,
            trading_date=trading_date,
        ).to_dict()
        results.append(result)
        if result["status"] != "PASSED":
            blockers.append(f"PAPER_SCENARIO_SUITE_{scenario_name.value}_{result['status']}")
    return _suite_result(results, blockers)


def run_paper_scenario(
    *,
    scenario_name: str | None,
    evidence_path: str | Path | None,
    trading_date: str = "2026-05-18",
    overrides: dict[str, Any] | None = None,
) -> PaperScenarioResult:
    blockers = validate_paper_scenario_inputs(scenario_name=scenario_name, evidence_path=evidence_path, overrides=overrides)
    scenario_text = _str_or_none(scenario_name)
    evidence_text = _normalize_path(evidence_path)
    if blockers:
        return PaperScenarioResult(
            scenario_name=scenario_text,
            status=PaperScenarioStatus.BLOCKED,
            evidence_path=evidence_text,
            blockers=blockers,
        )

    scenario = PaperScenarioName(str(scenario_text))
    session_id = build_paper_session_id(trading_date=trading_date, session_label=scenario.value)
    expected = _expected_for_scenario(scenario)
    inputs = _scenario_inputs(scenario, overrides or {})

    start_boundary = mark_paper_session_boundary(
        evidence_path,
        session_id=session_id,
        boundary_type="SESSION_START",
        created_at_epoch=inputs["ts_epoch"],
        reason=f"start {scenario.value}",
        metadata=_safe_metadata(scenario=scenario.value),
    ).to_dict()
    if start_boundary["status"] == "BLOCKED":
        return _blocked_scenario(scenario.value, session_id, evidence_text, expected, {"start": start_boundary}, _prefixed("SESSION_START", start_boundary.get("blockers") or []), start_boundary.get("warnings") or [])

    pipeline = run_paper_trading_pipeline(
        cycle_id=inputs["cycle_id"],
        top_executable=inputs["top_executable"],
        execution_safety=inputs["execution_safety"],
        readiness=inputs["readiness"],
        market_data=inputs["market_data"],
        instrument_health=inputs["instrument_health"],
        quote=inputs["quote"],
        ts_epoch=inputs["ts_epoch"],
        now_epoch=inputs["now_epoch"],
        max_quote_age_sec=inputs["max_quote_age_sec"],
    ).to_dict()

    if _unexpected_pipeline_block(scenario, pipeline):
        return _blocked_scenario(scenario.value, session_id, evidence_text, expected, {"start": start_boundary}, _prefixed("PIPELINE", pipeline.get("blockers") or ["PAPER_SCENARIO_PIPELINE_BLOCKED"]), pipeline.get("warnings") or [], pipeline=pipeline)

    write_pipeline = write_paper_evidence_record(
        evidence_path,
        record_type="PAPER_SCENARIO_PIPELINE_RESULT",
        cycle_id=inputs["cycle_id"],
        candidate_id=pipeline.get("candidate_id"),
        strategy_id=pipeline.get("strategy_id"),
        created_at_epoch=inputs["ts_epoch"],
        source="paper_scenario_suite",
        payload=pipeline,
    ).to_dict()
    if write_pipeline["status"] == "BLOCKED":
        return _blocked_scenario(scenario.value, session_id, evidence_text, expected, {"start": start_boundary}, _prefixed("PERSISTENCE_WRITE", write_pipeline.get("blockers") or []), write_pipeline.get("warnings") or [], pipeline=pipeline, persistence={"write_pipeline": write_pipeline})

    reset_boundary: dict[str, Any] = {}
    if scenario == PaperScenarioName.SESSION_RESET_MARKER_PATH:
        reset_boundary = mark_paper_session_boundary(
            evidence_path,
            session_id=session_id,
            boundary_type="RESET_MARKER",
            created_at_epoch=inputs["ts_epoch"] + 1.0,
            reason="future session isolation marker",
            metadata=_safe_metadata(scenario=scenario.value, reset_scope="future_only"),
        ).to_dict()
        if reset_boundary["status"] == "BLOCKED":
            return _blocked_scenario(scenario.value, session_id, evidence_text, expected, {"start": start_boundary, "reset": reset_boundary}, _prefixed("RESET_MARKER", reset_boundary.get("blockers") or []), reset_boundary.get("warnings") or [], pipeline=pipeline, persistence={"write_pipeline": write_pipeline})
    else:
        end_boundary = mark_paper_session_boundary(
            evidence_path,
            session_id=session_id,
            boundary_type="SESSION_END",
            created_at_epoch=inputs["ts_epoch"] + 1.0,
            reason=f"end {scenario.value}",
            metadata=_safe_metadata(scenario=scenario.value),
        ).to_dict()
        if end_boundary["status"] == "BLOCKED":
            return _blocked_scenario(scenario.value, session_id, evidence_text, expected, {"start": start_boundary, "end": end_boundary}, _prefixed("SESSION_END", end_boundary.get("blockers") or []), end_boundary.get("warnings") or [], pipeline=pipeline, persistence={"write_pipeline": write_pipeline})
        reset_boundary = end_boundary

    load_result = load_paper_evidence_records(evidence_path).to_dict()
    if load_result["status"] == "BLOCKED":
        return _blocked_scenario(scenario.value, session_id, evidence_text, expected, {"start": start_boundary, "boundary": reset_boundary}, _prefixed("PERSISTENCE_LOAD", load_result.get("blockers") or []), load_result.get("warnings") or [], pipeline=pipeline, persistence={"write_pipeline": write_pipeline, "load": load_result})

    actual = _actual_for_scenario(pipeline, load_result, reset_boundary)
    mismatches = _compare_expected(expected, actual)
    status = PaperScenarioStatus.PASSED if not mismatches else PaperScenarioStatus.FAILED
    return PaperScenarioResult(
        scenario_name=scenario.value,
        status=status,
        passed=status == PaperScenarioStatus.PASSED,
        session_id=session_id,
        evidence_path=evidence_text,
        expected=expected,
        actual=actual,
        pipeline=pipeline,
        session_boundaries={"start": start_boundary, "final": reset_boundary},
        persistence={"write_pipeline": write_pipeline, "load": load_result},
        blockers=mismatches,
        warnings=_dedupe([*(pipeline.get("warnings") or []), *(load_result.get("warnings") or [])]),
    )


def validate_paper_scenario_inputs(
    *,
    scenario_name: str | None,
    evidence_path: str | Path | None,
    overrides: dict[str, Any] | None = None,
) -> list[str]:
    blockers: list[str] = []
    scenario_text = _str_or_none(scenario_name)
    if not scenario_text:
        blockers.append("PAPER_SCENARIO_NAME_REQUIRED")
    elif scenario_text not in {name.value for name in PaperScenarioName}:
        blockers.append("PAPER_SCENARIO_NAME_UNKNOWN")
    if evidence_path is None or not _normalize_path(evidence_path):
        blockers.append("PAPER_SCENARIO_EVIDENCE_PATH_REQUIRED")
    if overrides is not None:
        if not isinstance(overrides, dict):
            blockers.append("PAPER_SCENARIO_OVERRIDES_MUST_BE_OBJECT")
        else:
            blockers.extend(_unsafe_payload_blockers("OVERRIDES", overrides))
    return _dedupe(blockers)


def _scenario_inputs(scenario: PaperScenarioName, overrides: dict[str, Any]) -> dict[str, Any]:
    top_executable = _deep_merge(_top(), overrides.get("top_executable") or {})
    execution_safety = _deep_merge(_safety(), overrides.get("execution_safety") or {})
    readiness = _deep_merge(_readiness(), overrides.get("readiness") or {})
    market_data = _deep_merge(_market_data(), overrides.get("market_data") or {})
    instrument_health = _deep_merge(_instrument_health(), overrides.get("instrument_health") or {})
    quote = _quote()
    max_quote_age_sec = 5.0
    now_epoch = 105.0
    if scenario == PaperScenarioName.PARTIAL_FILL_PATH:
        quote = _quote(available_quantity=4)
    elif scenario == PaperScenarioName.NO_FILL_PATH:
        quote = _quote(ask=101.0)
    elif scenario == PaperScenarioName.STALE_QUOTE_BLOCKED_PATH:
        quote = _quote(ts_epoch=1.0)
        now_epoch = 105.0
        max_quote_age_sec = 5.0
    quote = _deep_merge(quote, overrides.get("quote") or {})
    return {
        "cycle_id": str(overrides.get("cycle_id") or f"cycle-{scenario.value.lower()}"),
        "top_executable": top_executable,
        "execution_safety": execution_safety,
        "readiness": readiness,
        "market_data": market_data,
        "instrument_health": instrument_health,
        "quote": quote,
        "ts_epoch": float(overrides.get("ts_epoch") or 100.0),
        "now_epoch": float(overrides.get("now_epoch") or now_epoch),
        "max_quote_age_sec": float(overrides.get("max_quote_age_sec") or max_quote_age_sec),
    }


def _expected_for_scenario(scenario: PaperScenarioName) -> dict[str, Any]:
    if scenario == PaperScenarioName.PARTIAL_FILL_PATH:
        return {"pipeline_status": "COMPLETED", "last_event_type": "PAPER_ORDER_PARTIALLY_FILLED", "min_record_count": 3}
    if scenario == PaperScenarioName.NO_FILL_PATH:
        return {"pipeline_status": "COMPLETED", "last_event_type": "PAPER_ORDER_OPENED", "min_record_count": 3}
    if scenario == PaperScenarioName.STALE_QUOTE_BLOCKED_PATH:
        return {"pipeline_status": "BLOCKED", "last_event_type": None, "min_record_count": 3}
    if scenario == PaperScenarioName.SESSION_RESET_MARKER_PATH:
        return {"pipeline_status": "COMPLETED", "last_event_type": "PAPER_ORDER_FILLED", "min_record_count": 3, "final_boundary_type": "RESET_MARKER"}
    return {"pipeline_status": "COMPLETED", "last_event_type": "PAPER_ORDER_FILLED", "min_record_count": 3}


def _actual_for_scenario(pipeline: dict[str, Any], load_result: dict[str, Any], final_boundary: dict[str, Any]) -> dict[str, Any]:
    events = pipeline.get("events") if isinstance(pipeline.get("events"), list) else []
    final_record = final_boundary.get("record") if isinstance(final_boundary.get("record"), dict) else {}
    return {
        "pipeline_status": pipeline.get("status"),
        "last_event_type": events[-1].get("event_type") if events else None,
        "event_count": pipeline.get("event_count"),
        "record_count": load_result.get("record_count"),
        "final_boundary_type": final_record.get("boundary_type"),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _compare_expected(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key, expected_value in expected.items():
        if key == "min_record_count":
            if int(actual.get("record_count") or 0) < int(expected_value):
                blockers.append(f"PAPER_SCENARIO_EXPECTED_MIN_RECORD_COUNT_{expected_value}_GOT_{actual.get('record_count')}")
        elif actual.get(key) != expected_value:
            blockers.append(f"PAPER_SCENARIO_EXPECTED_{key.upper()}_{expected_value}_GOT_{actual.get(key)}")
    return blockers


def _unexpected_pipeline_block(scenario: PaperScenarioName, pipeline: dict[str, Any]) -> bool:
    if scenario == PaperScenarioName.STALE_QUOTE_BLOCKED_PATH:
        return pipeline.get("status") != "BLOCKED"
    return pipeline.get("status") == "BLOCKED"


def _blocked_scenario(
    scenario_name: str | None,
    session_id: str | None,
    evidence_path: str | None,
    expected: dict[str, Any],
    session_boundaries: dict[str, Any],
    blockers: list[str],
    warnings: list[str],
    *,
    pipeline: dict[str, Any] | None = None,
    persistence: dict[str, Any] | None = None,
) -> PaperScenarioResult:
    return PaperScenarioResult(
        scenario_name=scenario_name,
        status=PaperScenarioStatus.BLOCKED,
        passed=False,
        session_id=session_id,
        evidence_path=evidence_path,
        expected=expected,
        pipeline=pipeline or {},
        session_boundaries=session_boundaries,
        persistence=persistence or {},
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
    )


def _suite_result(results: list[dict[str, Any]], blockers: list[str]) -> dict[str, Any]:
    status = "PASSED" if not blockers else "FAILED"
    return {
        "schema_version": PAPER_SCENARIO_SCHEMA_VERSION,
        "suite_type": "PAPER_STANDARD_SCENARIO_SUITE",
        "status": status,
        "passed": not blockers,
        "scenario_count": len(results),
        "results": deepcopy(results),
        "blockers": list(blockers),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _top(candidate_id: str = "candidate-1", **selected_overrides: Any) -> dict[str, Any]:
    selected = {
        "candidate_id": candidate_id,
        "symbol": "NIFTY26MAY25500CE",
        "tradingsymbol": "NIFTY26MAY25500CE",
        "instrument_token": 12345,
        "transaction_type": "BUY",
        "quantity": 10,
        "order_type": "LIMIT",
        "product": "MIS",
        "price": 100.5,
        "trigger_price": 95.0,
        "strategy": "orb_retest",
        "quality_score": 91.0,
        "is_order": False,
    }
    selected.update(selected_overrides)
    return {"status": "SELECTED", "selected": selected, "is_order_action": False}


def _safety(**overrides: Any) -> dict[str, Any]:
    payload = {
        "execution_permitted": True,
        "status": "PERMITTED",
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "safety_visibility_only": True,
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def _readiness(**overrides: Any) -> dict[str, Any]:
    payload = {
        "candidate_id": "candidate-1",
        "readiness_status": "RESOLVED_EXACT",
        "resolved": True,
        "instrument_token": 12345,
        "fallback_used": False,
        "blockers": [],
        "warnings": [],
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _market_data(**overrides: Any) -> dict[str, Any]:
    payload = {
        "guard_type": "MARKET_SESSION_EXPIRY_CONTEXT_GUARD",
        "status": "READY",
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "session_open": True,
        "expiry_valid": True,
        "blockers": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def _instrument_health(**overrides: Any) -> dict[str, Any]:
    payload = {
        "panel_type": "INSTRUMENT_RESOLUTION_HEALTH_PANEL",
        "status": "HEALTHY",
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "summary": {"resolved_count": 1, "unresolved_count": 0},
        "blockers": [],
        "warnings": [],
    }
    payload.update(overrides)
    return payload


def _quote(**overrides: Any) -> dict[str, Any]:
    payload = {
        "source": "CONTROLLED_QUOTE",
        "ts_epoch": 104.0,
        "ask": 100.0,
        "bid": 99.5,
        "last": 99.75,
        "available_quantity": 10,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _safe_metadata(**overrides: Any) -> dict[str, Any]:
    payload = {
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }
    payload.update(overrides)
    return payload


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _unsafe_payload_blockers(name: str, payload: Any) -> list[str]:
    if payload is None:
        return []
    if not isinstance(payload, dict):
        return [f"PAPER_SCENARIO_{name}_MUST_BE_OBJECT"]
    blockers: list[str] = []
    for path, key, value in _walk_dict(payload):
        if key == "paper_only" and value is not True:
            blockers.append(f"PAPER_SCENARIO_{name}_{path}_UNSAFE_PAPER_ONLY_FLAG")
        if key == "read_only" and value is not True:
            blockers.append(f"PAPER_SCENARIO_{name}_{path}_UNSAFE_READ_ONLY_FLAG")
        if key == "is_order_action" and value is not False:
            blockers.append(f"PAPER_SCENARIO_{name}_{path}_UNSAFE_ORDER_ACTION_FLAG")
        if key == "broker_api_called" and value is True:
            blockers.append(f"PAPER_SCENARIO_{name}_{path}_BROKER_API_CALLED")
        if key == "real_order_id" and value not in (None, ""):
            blockers.append(f"PAPER_SCENARIO_{name}_{path}_REAL_ORDER_ID_PRESENT")
    return blockers


def _walk_dict(payload: dict[str, Any], prefix: str = "ROOT"):
    for key, value in payload.items():
        path = f"{prefix}_{str(key).upper()}"
        yield path, str(key), value
        if isinstance(value, dict):
            yield from _walk_dict(value, prefix=path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    yield from _walk_dict(item, prefix=f"{path}_{index}")


def _normalize_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    if isinstance(path, Path):
        return str(path)
    if isinstance(path, str):
        text = path.strip()
        return text or None
    return None


def _str_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _prefixed(source: str, blockers: list[str]) -> list[str]:
    return [f"PAPER_SCENARIO_{source}_{blocker}" for blocker in blockers]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

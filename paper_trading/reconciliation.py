from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


PAPER_STATE_RECONCILIATION_SCHEMA_VERSION = "1.0"
PAPER_STATE_REQUIRED_KEYS = [
    "schema_version",
    "state_type",
    "orders",
    "positions",
    "pnl_marks",
    "slippage_measurements",
    "performance_snapshots",
    "applied_event_ids",
    "applied_idempotency_keys",
    "last_event",
    "summary",
    "paper_only",
    "read_only",
    "is_order_action",
    "broker_api_called",
    "real_order_id",
]
COMPARE_KEYS = [
    "orders",
    "positions",
    "summary",
    "applied_event_ids",
    "applied_idempotency_keys",
    "last_event",
]


class PaperStateReconciliationStatus(StrEnum):
    MATCH = "MATCH"
    DRIFT = "DRIFT"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperStateReconciliationResult:
    matched: bool
    status: PaperStateReconciliationStatus
    drift_count: int = 0
    drifts: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    rebuilt_state_summary: dict[str, Any] = field(default_factory=dict)
    observed_state_summary: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = PAPER_STATE_RECONCILIATION_SCHEMA_VERSION

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
            "report_type": "PAPER_STATE_RECONCILIATION_REPORT",
            "status": self.status.value,
            "matched": self.matched,
            "drift_count": self.drift_count,
            "drifts": deepcopy(self.drifts),
            "summary": deepcopy(self.summary),
            "rebuilt_state_summary": deepcopy(self.rebuilt_state_summary),
            "observed_state_summary": deepcopy(self.observed_state_summary),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "paper_only": self.paper_only,
            "read_only": self.read_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_state_reconciliation_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_STATE_RECONCILIATION_SCHEMA_VERSION,
        "report_type": "PAPER_STATE_RECONCILIATION_REPORT",
        "consumes": ["PAPER_STATE_REBUILD_CLI", "PAPER_REDUCED_STATE"],
        "statuses": [status.value for status in PaperStateReconciliationStatus],
        "compared_state_keys": list(COMPARE_KEYS),
        "required_state_keys": list(PAPER_STATE_REQUIRED_KEYS),
        "required_result_keys": [
            "schema_version",
            "report_type",
            "status",
            "matched",
            "drift_count",
            "drifts",
            "summary",
            "rebuilt_state_summary",
            "observed_state_summary",
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
        "cli_exit_codes": {"MATCH": 0, "EMPTY": 0, "DRIFT": 1, "BLOCKED": 2},
        "scope_boundary": [
            "read_only_report_only",
            "no_state_mutation",
            "no_journal_append",
            "no_persistence_layer",
            "no_api",
            "no_ui",
            "no_runtime_wiring",
        ],
    }


def reconcile_paper_state(
    rebuild_result: dict[str, Any] | Any,
    observed_state: dict[str, Any] | None = None,
) -> PaperStateReconciliationResult:
    rebuild_payload = _to_dict(rebuild_result)
    blockers = validate_paper_state_reconciliation_inputs(rebuild_payload, observed_state)
    if blockers:
        return PaperStateReconciliationResult(
            matched=False,
            status=PaperStateReconciliationStatus.BLOCKED,
            blockers=blockers,
        )

    rebuilt_state = dict(rebuild_payload["state"])
    if _is_empty_rebuilt(rebuild_payload, rebuilt_state) and _observed_missing_or_empty(observed_state):
        return PaperStateReconciliationResult(
            matched=True,
            status=PaperStateReconciliationStatus.EMPTY,
            drift_count=0,
            drifts=[],
            summary=_summary(status="EMPTY", drift_count=0),
            rebuilt_state_summary=_state_summary(rebuilt_state),
            observed_state_summary=_state_summary(observed_state),
            warnings=["PAPER_STATE_RECONCILIATION_EMPTY_STATE"],
        )

    if observed_state is None:
        drifts = [_drift("observed_state", rebuilt_state, None, "OBSERVED_STATE_MISSING")]
    else:
        drifts = _compare_states(rebuilt_state, observed_state)

    if drifts:
        return PaperStateReconciliationResult(
            matched=False,
            status=PaperStateReconciliationStatus.DRIFT,
            drift_count=len(drifts),
            drifts=drifts,
            summary=_summary(status="DRIFT", drift_count=len(drifts)),
            rebuilt_state_summary=_state_summary(rebuilt_state),
            observed_state_summary=_state_summary(observed_state),
        )

    return PaperStateReconciliationResult(
        matched=True,
        status=PaperStateReconciliationStatus.MATCH,
        drift_count=0,
        drifts=[],
        summary=_summary(status="MATCH", drift_count=0),
        rebuilt_state_summary=_state_summary(rebuilt_state),
        observed_state_summary=_state_summary(observed_state),
    )


def validate_paper_state_reconciliation_inputs(
    rebuild_result: dict[str, Any] | None,
    observed_state: dict[str, Any] | None = None,
) -> list[str]:
    if rebuild_result is None:
        return ["PAPER_STATE_RECONCILIATION_REBUILD_RESULT_REQUIRED"]
    if not isinstance(rebuild_result, dict):
        return ["PAPER_STATE_RECONCILIATION_REBUILD_RESULT_MUST_BE_OBJECT"]

    blockers: list[str] = []
    status = rebuild_result.get("status")
    if status == "BLOCKED":
        blockers.append("PAPER_STATE_RECONCILIATION_REBUILD_RESULT_BLOCKED")
    if "state" not in rebuild_result:
        blockers.append("PAPER_STATE_RECONCILIATION_REBUILT_STATE_REQUIRED")
    elif not isinstance(rebuild_result.get("state"), dict):
        blockers.append("PAPER_STATE_RECONCILIATION_REBUILT_STATE_MUST_BE_OBJECT")
    else:
        blockers.extend(_state_blockers(rebuild_result["state"], source="REBUILT"))

    if observed_state is not None:
        if not isinstance(observed_state, dict):
            blockers.append("PAPER_STATE_RECONCILIATION_OBSERVED_STATE_MUST_BE_OBJECT")
        elif observed_state:
            blockers.extend(_state_blockers(observed_state, source="OBSERVED"))

    return _dedupe(blockers)


def _to_dict(value: dict[str, Any] | Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        payload = to_dict()
        return dict(payload) if isinstance(payload, dict) else None
    return None


def _state_blockers(state: dict[str, Any], source: str) -> list[str]:
    blockers: list[str] = []
    for key in PAPER_STATE_REQUIRED_KEYS:
        if key not in state:
            blockers.append(f"PAPER_STATE_RECONCILIATION_{source}_STATE_MISSING_{key.upper()}")
    if state.get("paper_only") is not True:
        blockers.append(f"PAPER_STATE_RECONCILIATION_{source}_STATE_UNSAFE_PAPER_ONLY_FLAG")
    if state.get("read_only") is not True:
        blockers.append(f"PAPER_STATE_RECONCILIATION_{source}_STATE_UNSAFE_READ_ONLY_FLAG")
    if state.get("is_order_action") is not False:
        blockers.append(f"PAPER_STATE_RECONCILIATION_{source}_STATE_UNSAFE_ORDER_ACTION_FLAG")
    if state.get("broker_api_called") is not False:
        blockers.append(f"PAPER_STATE_RECONCILIATION_{source}_STATE_UNSAFE_BROKER_API_FLAG")
    if state.get("real_order_id") is not None:
        blockers.append(f"PAPER_STATE_RECONCILIATION_{source}_STATE_UNSAFE_REAL_ORDER_ID")
    return blockers


def _compare_states(rebuilt_state: dict[str, Any], observed_state: dict[str, Any]) -> list[dict[str, Any]]:
    drifts: list[dict[str, Any]] = []
    for key in COMPARE_KEYS:
        rebuilt_value = rebuilt_state.get(key)
        observed_value = observed_state.get(key)
        if rebuilt_value != observed_value:
            if isinstance(rebuilt_value, dict) and isinstance(observed_value, dict):
                drifts.extend(_compare_dict(f"{key}", rebuilt_value, observed_value))
            else:
                drifts.append(_drift(key, rebuilt_value, observed_value, "VALUE_MISMATCH"))
    return drifts


def _compare_dict(path: str, rebuilt: dict[str, Any], observed: dict[str, Any]) -> list[dict[str, Any]]:
    drifts: list[dict[str, Any]] = []
    for key in sorted(set(rebuilt) | set(observed)):
        child_path = f"{path}.{key}"
        rebuilt_value = rebuilt.get(key)
        observed_value = observed.get(key)
        if isinstance(rebuilt_value, dict) and isinstance(observed_value, dict):
            drifts.extend(_compare_dict(child_path, rebuilt_value, observed_value))
        elif rebuilt_value != observed_value:
            reason = "MISSING_IN_OBSERVED" if key in rebuilt and key not in observed else "MISSING_IN_REBUILT" if key in observed and key not in rebuilt else "VALUE_MISMATCH"
            drifts.append(_drift(child_path, rebuilt_value, observed_value, reason))
    return drifts


def _drift(path: str, rebuilt: Any, observed: Any, reason: str) -> dict[str, Any]:
    return {
        "path": path,
        "reason": reason,
        "rebuilt": deepcopy(rebuilt),
        "observed": deepcopy(observed),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _is_empty_rebuilt(rebuild_payload: dict[str, Any], rebuilt_state: dict[str, Any]) -> bool:
    if rebuild_payload.get("status") == "EMPTY":
        return True
    summary = rebuilt_state.get("summary") if isinstance(rebuilt_state.get("summary"), dict) else {}
    return int(summary.get("event_count") or 0) == 0


def _observed_missing_or_empty(observed_state: dict[str, Any] | None) -> bool:
    if observed_state is None or observed_state == {}:
        return True
    summary = observed_state.get("summary") if isinstance(observed_state.get("summary"), dict) else {}
    return int(summary.get("event_count") or 0) == 0


def _state_summary(state: dict[str, Any] | None) -> dict[str, Any]:
    if not state:
        return {
            "event_count": 0,
            "order_count": 0,
            "position_count": 0,
            "paper_only": True,
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        }
    summary = state.get("summary") if isinstance(state.get("summary"), dict) else {}
    return {
        "event_count": int(summary.get("event_count") or 0),
        "order_count": len(state.get("orders") or {}),
        "position_count": len(state.get("positions") or {}),
        "last_event": deepcopy(state.get("last_event")),
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _summary(status: str, drift_count: int) -> dict[str, Any]:
    return {
        "status": status,
        "drift_count": drift_count,
        "paper_only": True,
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

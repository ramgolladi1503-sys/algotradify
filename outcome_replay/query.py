from __future__ import annotations

from typing import Any

from outcome_replay.replay import OutcomeStatus


_STATUS_ALIASES = {
    "SELECTED": OutcomeStatus.SELECTED,
    "TOP_EXECUTABLE_SELECTED": OutcomeStatus.SELECTED,
    "BLOCKED": OutcomeStatus.BLOCKED,
    "NO_ELIGIBLE_CANDIDATES": OutcomeStatus.BLOCKED,
    "ORDER_SUBMITTED": OutcomeStatus.SUBMITTED,
    "SUBMITTED": OutcomeStatus.SUBMITTED,
    "ORDER_ACCEPTED": OutcomeStatus.ACCEPTED,
    "ACCEPTED": OutcomeStatus.ACCEPTED,
    "OPEN": OutcomeStatus.ACCEPTED,
    "ORDER_REJECTED": OutcomeStatus.REJECTED,
    "REJECTED": OutcomeStatus.REJECTED,
    "PARTIALLY_FILLED": OutcomeStatus.PARTIALLY_FILLED,
    "PARTIAL": OutcomeStatus.PARTIALLY_FILLED,
    "FILLED": OutcomeStatus.FILLED,
    "COMPLETE": OutcomeStatus.FILLED,
    "EXIT_FILLED": OutcomeStatus.EXITED,
    "EXITED": OutcomeStatus.EXITED,
    "POSITION_CLOSED": OutcomeStatus.CLOSED,
    "CLOSED": OutcomeStatus.CLOSED,
}


def filter_outcome_replay_records(
    records: list[dict[str, Any]],
    *,
    candidate_id: str | None = None,
    status: str | None = None,
    strategy: str | None = None,
    ts_from_epoch: float | None = None,
    ts_to_epoch: float | None = None,
) -> list[dict[str, Any]]:
    allowed_statuses = _status_filter_set(status)
    strategy_key = _norm(strategy)
    filtered: list[dict[str, Any]] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        if candidate_id and _candidate_id(row) != candidate_id:
            continue
        if allowed_statuses and _row_status(row) not in allowed_statuses:
            continue
        if strategy_key and _norm(_row_strategy(row)) != strategy_key:
            continue
        ts_epoch = _num(row.get("ts_epoch") or row.get("timestamp") or row.get("time"))
        if ts_from_epoch is not None and (ts_epoch is None or ts_epoch < ts_from_epoch):
            continue
        if ts_to_epoch is not None and (ts_epoch is None or ts_epoch > ts_to_epoch):
            continue
        filtered.append(row)
    return filtered


def replay_query_metadata(
    *,
    candidate_id: str | None = None,
    status: str | None = None,
    strategy: str | None = None,
    ts_from_epoch: float | None = None,
    ts_to_epoch: float | None = None,
    source_count: int = 0,
    result_count: int = 0,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "status": status,
        "strategy": strategy,
        "ts_from_epoch": ts_from_epoch,
        "ts_to_epoch": ts_to_epoch,
        "source_count": source_count,
        "result_count": result_count,
        "read_only": True,
        "is_order_action": False,
    }


def _candidate_id(row: dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("trade_id") or row.get("client_order_id") or "unknown")


def _row_status(row: dict[str, Any]) -> OutcomeStatus:
    return _normalize_status(row.get("outcome_status") or row.get("status") or row.get("event") or row.get("current_status"))


def _status_filter_set(status: str | None) -> set[OutcomeStatus]:
    if not status:
        return set()
    statuses: set[OutcomeStatus] = set()
    for raw in str(status).split(","):
        normalized = _normalize_status(raw)
        if normalized != OutcomeStatus.UNKNOWN:
            statuses.add(normalized)
    return statuses


def _normalize_status(value: Any) -> OutcomeStatus:
    key = _norm(value)
    return _STATUS_ALIASES.get(key, OutcomeStatus.UNKNOWN)


def _row_strategy(row: dict[str, Any]) -> str | None:
    for payload in (row, row.get("evidence") if isinstance(row.get("evidence"), dict) else {}):
        for key in ("strategy", "strategy_id", "strategy_family", "setup_family"):
            value = payload.get(key) if isinstance(payload, dict) else None
            if value not in (None, ""):
                return str(value)
    selected = row.get("selected") if isinstance(row.get("selected"), dict) else None
    if selected:
        for key in ("strategy", "strategy_id", "strategy_family", "setup_family"):
            value = selected.get(key)
            if value not in (None, ""):
                return str(value)
    return None


def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _norm(value: Any) -> str:
    return str(value or "").upper().strip().replace(" ", "_").replace("-", "_")

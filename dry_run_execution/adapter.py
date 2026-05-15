from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DryRunOrderIntent:
    dry_run_order_id: str
    candidate_id: str
    symbol: str | None = None
    tradingsymbol: str | None = None
    instrument_token: str | None = None
    transaction_type: str | None = None
    quantity: int | None = None
    order_type: str | None = None
    product: str | None = None
    price: float | None = None
    trigger_price: float | None = None
    strategy: str | None = None
    quality_score: float | None = None
    approval_id: str | None = None
    operator_id: str | None = None
    created_at_epoch: float | None = None
    source: str = "dry_run_execution_adapter"
    top_executable_snapshot: dict[str, Any] = field(default_factory=dict)
    execution_safety_snapshot: dict[str, Any] = field(default_factory=dict)
    approval_snapshot: dict[str, Any] = field(default_factory=dict)
    readiness_snapshot: dict[str, Any] = field(default_factory=dict)

    @property
    def dry_run_only(self) -> bool:
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
            "dry_run_order_id": self.dry_run_order_id,
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "tradingsymbol": self.tradingsymbol,
            "instrument_token": self.instrument_token,
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "product": self.product,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "strategy": self.strategy,
            "quality_score": self.quality_score,
            "approval_id": self.approval_id,
            "operator_id": self.operator_id,
            "created_at_epoch": self.created_at_epoch,
            "source": self.source,
            "top_executable_snapshot": dict(self.top_executable_snapshot),
            "execution_safety_snapshot": dict(self.execution_safety_snapshot),
            "approval_snapshot": dict(self.approval_snapshot),
            "readiness_snapshot": dict(self.readiness_snapshot),
            "dry_run_only": self.dry_run_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


@dataclass(frozen=True)
class DryRunLifecycleEvent:
    dry_run_order_id: str
    candidate_id: str
    status: str = "DRY_RUN_INTENT_CREATED"
    ts_epoch: float | None = None
    source: str = "dry_run_execution_adapter"
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def dry_run_only(self) -> bool:
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
            "dry_run_order_id": self.dry_run_order_id,
            "candidate_id": self.candidate_id,
            "status": self.status,
            "ts_epoch": self.ts_epoch,
            "source": self.source,
            "evidence": dict(self.evidence),
            "dry_run_only": self.dry_run_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


@dataclass(frozen=True)
class DryRunExecutionResult:
    created: bool
    intent: DryRunOrderIntent | None = None
    lifecycle_event: DryRunLifecycleEvent | None = None
    outcome_event: dict[str, Any] | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    append_paths: dict[str, str] = field(default_factory=dict)

    @property
    def dry_run_only(self) -> bool:
        return True

    @property
    def is_order_action(self) -> bool:
        return False

    @property
    def broker_api_called(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "intent": self.intent.to_dict() if self.intent else None,
            "lifecycle_event": self.lifecycle_event.to_dict() if self.lifecycle_event else None,
            "outcome_event": dict(self.outcome_event) if self.outcome_event else None,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "append_paths": dict(self.append_paths),
            "dry_run_only": self.dry_run_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
        }


def build_dry_run_execution(
    *,
    top_executable: dict[str, Any] | None,
    execution_safety: dict[str, Any] | None,
    approval: dict[str, Any] | None,
    readiness: dict[str, Any] | None = None,
    ts_epoch: float | None = None,
) -> DryRunExecutionResult:
    blockers, warnings = validate_dry_run_execution(
        top_executable=top_executable,
        execution_safety=execution_safety,
        approval=approval,
    )
    if blockers:
        return DryRunExecutionResult(created=False, blockers=blockers, warnings=warnings)

    selected = _selected(top_executable) or {}
    candidate_id = str(selected.get("candidate_id"))
    dry_run_order_id = _stable_dry_run_order_id(candidate_id, approval, ts_epoch)
    intent = DryRunOrderIntent(
        dry_run_order_id=dry_run_order_id,
        candidate_id=candidate_id,
        symbol=_str_or_none(selected.get("symbol") or selected.get("underlying")),
        tradingsymbol=_str_or_none(selected.get("tradingsymbol") or selected.get("symbol")),
        instrument_token=_str_or_none(selected.get("instrument_token")),
        transaction_type=_str_or_none(selected.get("transaction_type") or selected.get("side")),
        quantity=_int_or_none(selected.get("quantity") or selected.get("qty")),
        order_type=_str_or_none(selected.get("order_type")),
        product=_str_or_none(selected.get("product")),
        price=_float_or_none(selected.get("price") or selected.get("entry") or selected.get("entry_price")),
        trigger_price=_float_or_none(selected.get("trigger_price") or selected.get("stop") or selected.get("stop_loss")),
        strategy=_str_or_none(selected.get("strategy") or selected.get("strategy_id") or selected.get("setup_family")),
        quality_score=_float_or_none(selected.get("quality_score") or selected.get("score")),
        approval_id=_str_or_none((approval or {}).get("approval_id")),
        operator_id=_str_or_none((approval or {}).get("operator_id")),
        created_at_epoch=ts_epoch,
        top_executable_snapshot=dict(top_executable or {}),
        execution_safety_snapshot=dict(execution_safety or {}),
        approval_snapshot=dict(approval or {}),
        readiness_snapshot=dict(readiness or {}),
    )
    lifecycle = DryRunLifecycleEvent(
        dry_run_order_id=dry_run_order_id,
        candidate_id=candidate_id,
        ts_epoch=ts_epoch,
        evidence={
            "dry_run_order_id": dry_run_order_id,
            "dry_run_only": True,
            "broker_api_called": False,
            "real_order_id": None,
            "approval_id": intent.approval_id,
            "execution_safety_status": (execution_safety or {}).get("status"),
        },
    )
    outcome = _outcome_event(intent, execution_safety, ts_epoch)
    return DryRunExecutionResult(created=True, intent=intent, lifecycle_event=lifecycle, outcome_event=outcome, warnings=warnings)


def validate_dry_run_execution(
    *,
    top_executable: dict[str, Any] | None,
    execution_safety: dict[str, Any] | None,
    approval: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    selected = _selected(top_executable)
    if not selected:
        blockers.append("NO_TOP_EXECUTABLE_SELECTED")
    elif selected.get("is_order") is not False:
        blockers.append("TOP_EXECUTABLE_ORDER_FLAG_UNSAFE")

    if not isinstance(execution_safety, dict) or not execution_safety:
        blockers.append("EXECUTION_SAFETY_REQUIRED")
    else:
        if execution_safety.get("execution_permitted") is not True:
            blockers.append("EXECUTION_SAFETY_NOT_PERMITTED")
        if execution_safety.get("is_order_action") is not False:
            blockers.append("EXECUTION_SAFETY_ORDER_FLAG_UNSAFE")

    if not isinstance(approval, dict) or not approval:
        blockers.append("APPROVAL_EVIDENCE_REQUIRED")
    else:
        if approval.get("current_status") != "APPROVED":
            blockers.append("APPROVAL_NOT_APPROVED")
        if approval.get("is_order_action") is not False:
            blockers.append("APPROVAL_ORDER_FLAG_UNSAFE")
        if approval.get("blockers"):
            warnings.append("APPROVAL_HAS_BLOCKERS")

    candidate_id = selected.get("candidate_id") if isinstance(selected, dict) else None
    approval_candidate_id = approval.get("candidate_id") if isinstance(approval, dict) else None
    if candidate_id in (None, ""):
        blockers.append("CANDIDATE_ID_REQUIRED")
    if candidate_id and approval_candidate_id and str(candidate_id) != str(approval_candidate_id):
        blockers.append("APPROVAL_CANDIDATE_MISMATCH")

    if isinstance(approval, dict):
        events = approval.get("events") if isinstance(approval.get("events"), list) else []
        if events:
            latest = events[-1]
            safety = latest.get("safety_decision") if isinstance(latest, dict) else {}
            if isinstance(safety, dict) and safety.get("is_order_action") is not False:
                blockers.append("APPROVAL_SAFETY_SNAPSHOT_UNSAFE")

    return _dedupe(blockers), _dedupe(warnings)


def append_dry_run_execution(root: Path, result: DryRunExecutionResult) -> DryRunExecutionResult:
    if not result.created or result.intent is None or result.lifecycle_event is None or result.outcome_event is None:
        return result
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    paths = {
        "intent": logs / "dry_run_order_intents.jsonl",
        "lifecycle": logs / "dry_run_lifecycle.jsonl",
        "outcome": logs / "outcome_replay.jsonl",
    }
    _append_jsonl(paths["intent"], result.intent.to_dict())
    _append_jsonl(paths["lifecycle"], result.lifecycle_event.to_dict())
    _append_jsonl(paths["outcome"], result.outcome_event)
    return DryRunExecutionResult(
        created=True,
        intent=result.intent,
        lifecycle_event=result.lifecycle_event,
        outcome_event=result.outcome_event,
        warnings=list(result.warnings),
        append_paths={key: str(path) for key, path in paths.items()},
    )


def _selected(top_executable: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(top_executable, dict):
        return None
    if top_executable.get("status") != "SELECTED":
        return None
    selected = top_executable.get("selected")
    return selected if isinstance(selected, dict) and selected else None


def _outcome_event(intent: DryRunOrderIntent, execution_safety: dict[str, Any] | None, ts_epoch: float | None) -> dict[str, Any]:
    return {
        "candidate_id": intent.candidate_id,
        "status": "SUBMITTED",
        "source": "dry_run_execution_adapter",
        "reason": "DRY_RUN_INTENT_CREATED",
        "quality_score": intent.quality_score,
        "ts_epoch": ts_epoch,
        "evidence": {
            "dry_run_order_id": intent.dry_run_order_id,
            "dry_run_only": True,
            "broker_api_called": False,
            "real_order_id": None,
            "approval_id": intent.approval_id,
            "execution_safety_status": (execution_safety or {}).get("status"),
        },
        "is_order_action": False,
        "dry_run_only": True,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _stable_dry_run_order_id(candidate_id: str, approval: dict[str, Any] | None, ts_epoch: float | None) -> str:
    seed = "|".join([candidate_id, str((approval or {}).get("approval_id") or ""), str(ts_epoch or "")])
    return f"dryrun-{sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def _str_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out

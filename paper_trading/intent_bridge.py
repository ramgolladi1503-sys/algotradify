from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any


PAPER_ORDER_INTENT_SCHEMA_VERSION = "1.0"
BLOCKING_CONTEXT_STATUSES = {
    "BLOCKED",
    "BLOCKED_PRE_OPEN",
    "BLOCKED_CLOSING",
    "BLOCKED_CLOSED",
    "BLOCKED_EXPIRED_CONTRACT",
    "BLOCKED_INVALID_EXPIRY",
    "BLOCKED_MISSING_CONTEXT",
    "BLOCKED_UNRESOLVED",
    "BLOCKED_MISSING_SPOT",
    "BLOCKED_STALE_SPOT",
    "BLOCKED_FALLBACK_SOURCE",
    "BLOCKED_MISSING_OPTION_CHAIN",
    "BLOCKED_STALE_OPTION_CHAIN",
    "BLOCKED_SESSION_CLOSED",
    "BLOCKED_MISSING_SIDE",
    "BLOCKED_ZERO_SIDE",
    "BLOCKED_SHALLOW_DEPTH",
    "BLOCKED_STALE_DEPTH",
    "BLOCKED_DEPTH_IMBALANCE",
    "EMPTY",
}


@dataclass(frozen=True)
class PaperOrderIntent:
    paper_order_intent_id: str
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
    created_at_epoch: float | None = None
    source: str = "paper_order_intent_bridge"
    candidate_snapshot: dict[str, Any] = field(default_factory=dict)
    readiness_snapshot: dict[str, Any] = field(default_factory=dict)
    market_data_snapshot: dict[str, Any] = field(default_factory=dict)
    instrument_health_snapshot: dict[str, Any] = field(default_factory=dict)
    safety_decision_snapshot: dict[str, Any] = field(default_factory=dict)

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
            "schema_version": PAPER_ORDER_INTENT_SCHEMA_VERSION,
            "intent_type": "PAPER_ORDER_INTENT",
            "paper_order_intent_id": self.paper_order_intent_id,
            "candidate_id": self.candidate_id,
            "status": "PAPER_INTENT_READY",
            "execution_mode": "PAPER",
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
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
            "created_at_epoch": self.created_at_epoch,
            "source": self.source,
            "candidate_snapshot": dict(self.candidate_snapshot),
            "readiness_snapshot": dict(self.readiness_snapshot),
            "market_data_snapshot": dict(self.market_data_snapshot),
            "instrument_health_snapshot": dict(self.instrument_health_snapshot),
            "safety_decision_snapshot": dict(self.safety_decision_snapshot),
        }


@dataclass(frozen=True)
class PaperOrderIntentResult:
    created: bool
    intent: PaperOrderIntent | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: str = PAPER_ORDER_INTENT_SCHEMA_VERSION

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
            "bridge_type": "PAPER_ORDER_INTENT_BRIDGE",
            "created": self.created,
            "intent": self.intent.to_dict() if self.intent else None,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_order_intent_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_ORDER_INTENT_SCHEMA_VERSION,
        "bridge_type": "PAPER_ORDER_INTENT_BRIDGE",
        "intent_type": "PAPER_ORDER_INTENT",
        "required_result_keys": [
            "schema_version",
            "bridge_type",
            "created",
            "intent",
            "blockers",
            "warnings",
            "evidence",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "required_intent_keys": [
            "schema_version",
            "intent_type",
            "paper_order_intent_id",
            "candidate_id",
            "status",
            "execution_mode",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
            "candidate_snapshot",
            "readiness_snapshot",
            "market_data_snapshot",
            "instrument_health_snapshot",
            "safety_decision_snapshot",
        ],
        "safe_flags": {
            "paper_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
    }


def build_paper_order_intent(
    *,
    top_executable: dict[str, Any] | None,
    execution_safety: dict[str, Any] | None,
    readiness: dict[str, Any] | None = None,
    market_data: dict[str, Any] | None = None,
    instrument_health: dict[str, Any] | None = None,
    ts_epoch: float | None = None,
) -> PaperOrderIntentResult:
    blockers, warnings = validate_paper_order_intent(
        top_executable=top_executable,
        execution_safety=execution_safety,
        readiness=readiness,
        market_data=market_data,
        instrument_health=instrument_health,
    )
    evidence = _evidence_snapshot(
        top_executable=top_executable,
        execution_safety=execution_safety,
        readiness=readiness,
        market_data=market_data,
        instrument_health=instrument_health,
    )
    if blockers:
        return PaperOrderIntentResult(created=False, blockers=blockers, warnings=warnings, evidence=evidence)

    selected = _selected(top_executable) or {}
    candidate_id = str(selected.get("candidate_id"))
    intent = PaperOrderIntent(
        paper_order_intent_id=_stable_paper_order_intent_id(candidate_id, ts_epoch),
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
        created_at_epoch=ts_epoch,
        candidate_snapshot=dict(selected),
        readiness_snapshot=dict(readiness or {}),
        market_data_snapshot=dict(market_data or {}),
        instrument_health_snapshot=dict(instrument_health or {}),
        safety_decision_snapshot=dict(execution_safety or {}),
    )
    return PaperOrderIntentResult(created=True, intent=intent, warnings=warnings, evidence=evidence)


def validate_paper_order_intent(
    *,
    top_executable: dict[str, Any] | None,
    execution_safety: dict[str, Any] | None,
    readiness: dict[str, Any] | None = None,
    market_data: dict[str, Any] | None = None,
    instrument_health: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    selected = _selected(top_executable)

    if not selected:
        blockers.append("NO_SELECTED_EXECUTABLE_CANDIDATE")
    elif selected.get("is_order") is not False:
        blockers.append("SELECTED_CANDIDATE_ORDER_FLAG_UNSAFE")

    if not isinstance(execution_safety, dict) or not execution_safety:
        blockers.append("EXECUTION_SAFETY_REQUIRED")
    else:
        if execution_safety.get("execution_permitted") is not True:
            blockers.append("EXECUTION_SAFETY_NOT_PERMITTED")
        if execution_safety.get("is_order_action") is not False:
            blockers.append("EXECUTION_SAFETY_ORDER_FLAG_UNSAFE")

    _validate_read_only_snapshot(readiness, blockers, warnings, snapshot_name="READINESS")
    _validate_read_only_snapshot(market_data, blockers, warnings, snapshot_name="MARKET_DATA")
    _validate_read_only_snapshot(instrument_health, blockers, warnings, snapshot_name="INSTRUMENT_HEALTH")
    _validate_context_status(market_data, blockers, warnings, snapshot_name="MARKET_DATA")
    _validate_context_status(instrument_health, blockers, warnings, snapshot_name="INSTRUMENT_HEALTH")
    _validate_readiness(readiness, blockers, warnings)

    candidate_id = selected.get("candidate_id") if isinstance(selected, dict) else None
    if candidate_id in (None, ""):
        blockers.append("CANDIDATE_ID_REQUIRED")

    return _dedupe(blockers), _dedupe(warnings)


def _validate_read_only_snapshot(
    snapshot: dict[str, Any] | None,
    blockers: list[str],
    warnings: list[str],
    *,
    snapshot_name: str,
) -> None:
    if not isinstance(snapshot, dict) or not snapshot:
        warnings.append(f"{snapshot_name}_SNAPSHOT_MISSING")
        return
    if snapshot.get("is_order_action") is not False:
        blockers.append(f"{snapshot_name}_ORDER_FLAG_UNSAFE")
    if snapshot.get("broker_api_called") is True:
        blockers.append(f"{snapshot_name}_BROKER_API_CALLED")
    if snapshot.get("real_order_id") not in (None, ""):
        blockers.append(f"{snapshot_name}_REAL_ORDER_ID_PRESENT")


def _validate_context_status(
    snapshot: dict[str, Any] | None,
    blockers: list[str],
    warnings: list[str],
    *,
    snapshot_name: str,
) -> None:
    if not isinstance(snapshot, dict) or not snapshot:
        return
    status = str(snapshot.get("status") or "").upper()
    if status in BLOCKING_CONTEXT_STATUSES or status.startswith("BLOCKED"):
        blockers.append(f"{snapshot_name}_BLOCKED")
    elif status.startswith("DEGRADED"):
        warnings.append(f"{snapshot_name}_DEGRADED")


def _validate_readiness(readiness: dict[str, Any] | None, blockers: list[str], warnings: list[str]) -> None:
    if not isinstance(readiness, dict) or not readiness:
        return
    if readiness.get("resolved") is False:
        blockers.append("READINESS_UNRESOLVED")
    if readiness.get("readiness_status") and str(readiness.get("readiness_status")).upper().startswith("BLOCKED"):
        blockers.append("READINESS_BLOCKED")
    if readiness.get("fallback_used") is True:
        warnings.append("READINESS_FALLBACK_USED")
    for blocker in readiness.get("blockers") or []:
        blockers.append(str(blocker))
    for warning in readiness.get("warnings") or []:
        warnings.append(str(warning))


def _selected(top_executable: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(top_executable, dict):
        return None
    if top_executable.get("status") != "SELECTED":
        return None
    selected = top_executable.get("selected")
    return selected if isinstance(selected, dict) and selected else None


def _evidence_snapshot(
    *,
    top_executable: dict[str, Any] | None,
    execution_safety: dict[str, Any] | None,
    readiness: dict[str, Any] | None,
    market_data: dict[str, Any] | None,
    instrument_health: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "top_executable_status": top_executable.get("status") if isinstance(top_executable, dict) else None,
        "execution_safety_status": execution_safety.get("status") if isinstance(execution_safety, dict) else None,
        "readiness_status": readiness.get("readiness_status") or readiness.get("status") if isinstance(readiness, dict) else None,
        "market_data_status": market_data.get("status") if isinstance(market_data, dict) else None,
        "instrument_health_status": instrument_health.get("status") if isinstance(instrument_health, dict) else None,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _stable_paper_order_intent_id(candidate_id: str, ts_epoch: float | None) -> str:
    seed = "|".join([candidate_id, str(ts_epoch or "")])
    return f"paper-{sha256(seed.encode('utf-8')).hexdigest()[:16]}"


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
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

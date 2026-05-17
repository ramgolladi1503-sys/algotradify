from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any


SUPPORTED_TRANSACTION_TYPES = ("BUY", "SELL")
SUPPORTED_ORDER_TYPES = ("MARKET", "LIMIT", "SL", "SL-M")
SUPPORTED_PRODUCTS = ("MIS", "NRML", "CNC")
ORDER_INTENT_CONTRACT_VERSION = "1.0"


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    candidate_id: str
    mode: str
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
    broker_confirmation_id: str | None = None
    created_at_epoch: float | None = None
    source: str = "order_intent_contract"
    top_executable_snapshot: dict[str, Any] = field(default_factory=dict)
    execution_safety_snapshot: dict[str, Any] = field(default_factory=dict)
    readiness_snapshot: dict[str, Any] = field(default_factory=dict)

    @property
    def contract_version(self) -> str:
        return ORDER_INTENT_CONTRACT_VERSION

    @property
    def is_order_action(self) -> bool:
        return False

    @property
    def broker_api_called(self) -> bool:
        return False

    @property
    def real_order_id(self) -> None:
        return None

    @property
    def requires_broker_adapter(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "candidate_id": self.candidate_id,
            "mode": self.mode,
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
            "broker_confirmation_id": self.broker_confirmation_id,
            "created_at_epoch": self.created_at_epoch,
            "source": self.source,
            "contract_version": self.contract_version,
            "top_executable_snapshot": dict(self.top_executable_snapshot),
            "execution_safety_snapshot": dict(self.execution_safety_snapshot),
            "readiness_snapshot": dict(self.readiness_snapshot),
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
            "requires_broker_adapter": self.requires_broker_adapter,
        }


@dataclass(frozen=True)
class OrderIntentBuildResult:
    created: bool
    intent: OrderIntent | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    contract_version: str = ORDER_INTENT_CONTRACT_VERSION

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
            "created": self.created,
            "intent": self.intent.to_dict() if self.intent else None,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "contract_version": self.contract_version,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def build_order_intent(
    *,
    top_executable: dict[str, Any] | None,
    execution_safety: dict[str, Any] | None,
    readiness: dict[str, Any] | None = None,
    ts_epoch: float | None = None,
) -> OrderIntentBuildResult:
    blockers, warnings = validate_order_intent_inputs(
        top_executable=top_executable,
        execution_safety=execution_safety,
        readiness=readiness,
    )
    if blockers:
        return OrderIntentBuildResult(created=False, blockers=blockers, warnings=warnings)

    selected = _selected(top_executable) or {}
    candidate_id = str(selected.get("candidate_id"))
    mode = str((execution_safety or {}).get("mode"))
    intent = OrderIntent(
        intent_id=_stable_intent_id(candidate_id, mode, execution_safety, ts_epoch),
        candidate_id=candidate_id,
        mode=mode,
        symbol=_str_or_none(selected.get("symbol") or selected.get("underlying")),
        tradingsymbol=_str_or_none(selected.get("tradingsymbol") or selected.get("symbol")),
        instrument_token=_str_or_none(selected.get("instrument_token")),
        transaction_type=_normalized_choice(selected.get("transaction_type") or selected.get("side"), SUPPORTED_TRANSACTION_TYPES),
        quantity=_int_or_none(selected.get("quantity") or selected.get("qty")),
        order_type=_normalized_choice(selected.get("order_type"), SUPPORTED_ORDER_TYPES),
        product=_normalized_choice(selected.get("product"), SUPPORTED_PRODUCTS),
        price=_float_or_none(selected.get("price") or selected.get("entry") or selected.get("entry_price")),
        trigger_price=_float_or_none(selected.get("trigger_price") or selected.get("stop") or selected.get("stop_loss")),
        strategy=_str_or_none(selected.get("strategy") or selected.get("strategy_id") or selected.get("setup_family")),
        quality_score=_float_or_none(selected.get("quality_score") or selected.get("score")),
        approval_id=_str_or_none((execution_safety or {}).get("audit", {}).get("policy", {}).get("approval_id")),
        operator_id=_str_or_none((execution_safety or {}).get("audit", {}).get("policy", {}).get("operator_id")),
        broker_confirmation_id=_str_or_none((execution_safety or {}).get("audit", {}).get("policy", {}).get("broker_confirmation_id")),
        created_at_epoch=ts_epoch,
        top_executable_snapshot=dict(top_executable or {}),
        execution_safety_snapshot=dict(execution_safety or {}),
        readiness_snapshot=dict(readiness or {}),
    )
    return OrderIntentBuildResult(created=True, intent=intent, warnings=warnings)


def validate_order_intent_inputs(
    *,
    top_executable: dict[str, Any] | None,
    execution_safety: dict[str, Any] | None,
    readiness: dict[str, Any] | None = None,
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
        if execution_safety.get("safety_visibility_only") is not True:
            blockers.append("EXECUTION_SAFETY_VISIBILITY_FLAG_REQUIRED")
        if execution_safety.get("mode") not in {"SIM", "PAPER", "LIVE"}:
            blockers.append("EXECUTION_MODE_UNSUPPORTED")
        if execution_safety.get("execution_mode_api_parse", {}).get("invalid_mode") is True:
            blockers.append("INVALID_EXECUTION_MODE")
        if execution_safety.get("broker_api_allowed") is True and execution_safety.get("mode") != "LIVE":
            blockers.append("BROKER_API_ALLOWED_ONLY_IN_LIVE")
        if execution_safety.get("real_order_allowed") is True and execution_safety.get("mode") != "LIVE":
            blockers.append("REAL_ORDER_ALLOWED_ONLY_IN_LIVE")

    if isinstance(readiness, dict) and readiness:
        if readiness.get("execution_allowed") is not True:
            blockers.append("READINESS_NOT_ALLOWED")
        if readiness.get("is_order") is not False:
            blockers.append("READINESS_ORDER_FLAG_UNSAFE")

    if isinstance(selected, dict):
        candidate_id = selected.get("candidate_id")
        if candidate_id in (None, ""):
            blockers.append("CANDIDATE_ID_REQUIRED")
        transaction_type = _normalized_choice(selected.get("transaction_type") or selected.get("side"), SUPPORTED_TRANSACTION_TYPES)
        if transaction_type is None:
            blockers.append("TRANSACTION_TYPE_REQUIRED_OR_UNSUPPORTED")
        quantity = _int_or_none(selected.get("quantity") or selected.get("qty"))
        if quantity is None or quantity <= 0:
            blockers.append("POSITIVE_QUANTITY_REQUIRED")
        order_type = _normalized_choice(selected.get("order_type"), SUPPORTED_ORDER_TYPES)
        if order_type is None:
            blockers.append("ORDER_TYPE_REQUIRED_OR_UNSUPPORTED")
        product = _normalized_choice(selected.get("product"), SUPPORTED_PRODUCTS)
        if product is None:
            blockers.append("PRODUCT_REQUIRED_OR_UNSUPPORTED")
        if order_type == "LIMIT" and _float_or_none(selected.get("price") or selected.get("entry") or selected.get("entry_price")) is None:
            blockers.append("LIMIT_PRICE_REQUIRED")
        if order_type in {"SL", "SL-M"} and _float_or_none(selected.get("trigger_price") or selected.get("stop") or selected.get("stop_loss")) is None:
            blockers.append("TRIGGER_PRICE_REQUIRED")

    candidate_id = selected.get("candidate_id") if isinstance(selected, dict) else None
    if isinstance(readiness, dict) and readiness.get("candidate_id") and candidate_id and str(readiness.get("candidate_id")) != str(candidate_id):
        blockers.append("READINESS_CANDIDATE_MISMATCH")

    return _dedupe(blockers), _dedupe(warnings)


def _selected(top_executable: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(top_executable, dict):
        return None
    if top_executable.get("status") != "SELECTED":
        return None
    selected = top_executable.get("selected")
    return selected if isinstance(selected, dict) and selected else None


def _stable_intent_id(candidate_id: str, mode: str, execution_safety: dict[str, Any] | None, ts_epoch: float | None) -> str:
    policy = (execution_safety or {}).get("audit", {}).get("policy", {}) if isinstance((execution_safety or {}).get("audit"), dict) else {}
    seed = "|".join(
        [
            candidate_id,
            mode,
            str(policy.get("approval_id") or ""),
            str(policy.get("broker_confirmation_id") or ""),
            str(ts_epoch or ""),
        ]
    )
    return f"intent-{sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def _normalized_choice(value: Any, allowed: tuple[str, ...]) -> str | None:
    if value in (None, ""):
        return None
    normalized = str(value).upper()
    return normalized if normalized in allowed else None


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

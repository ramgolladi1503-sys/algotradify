from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any


PAPER_BROKER_ADAPTER_VERSION = "1.0"
SUPPORTED_TRANSACTION_TYPES = ("BUY", "SELL")
SUPPORTED_ORDER_TYPES = ("MARKET", "LIMIT", "SL", "SL-M")
SUPPORTED_PRODUCTS = ("MIS", "NRML", "CNC")


@dataclass(frozen=True)
class PaperBrokerOrderAck:
    synthetic_order_id: str
    intent_id: str
    candidate_id: str
    status: str = "PAPER_ACCEPTED"
    mode: str = "PAPER"
    tradingsymbol: str | None = None
    transaction_type: str | None = None
    quantity: int | None = None
    order_type: str | None = None
    product: str | None = None
    price: float | None = None
    trigger_price: float | None = None
    created_at_epoch: float | None = None
    source: str = "paper_broker_adapter"
    intent_snapshot: dict[str, Any] = field(default_factory=dict)

    @property
    def adapter_version(self) -> str:
        return PAPER_BROKER_ADAPTER_VERSION

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
            "synthetic_order_id": self.synthetic_order_id,
            "intent_id": self.intent_id,
            "candidate_id": self.candidate_id,
            "status": self.status,
            "mode": self.mode,
            "tradingsymbol": self.tradingsymbol,
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "product": self.product,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "created_at_epoch": self.created_at_epoch,
            "source": self.source,
            "adapter_version": self.adapter_version,
            "intent_snapshot": dict(self.intent_snapshot),
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


@dataclass(frozen=True)
class PaperBrokerExecutionResult:
    accepted: bool
    ack: PaperBrokerOrderAck | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    adapter_version: str = PAPER_BROKER_ADAPTER_VERSION

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
            "accepted": self.accepted,
            "ack": self.ack.to_dict() if self.ack else None,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "adapter_version": self.adapter_version,
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def execute_paper_order(
    *,
    intent: dict[str, Any] | None,
    ts_epoch: float | None = None,
    broker_client: Any | None = None,
) -> PaperBrokerExecutionResult:
    blockers, warnings = validate_paper_order_intent(intent=intent, broker_client=broker_client)
    if blockers:
        return PaperBrokerExecutionResult(accepted=False, blockers=blockers, warnings=warnings)

    assert intent is not None
    synthetic_order_id = _stable_paper_order_id(intent, ts_epoch)
    ack = PaperBrokerOrderAck(
        synthetic_order_id=synthetic_order_id,
        intent_id=str(intent.get("intent_id")),
        candidate_id=str(intent.get("candidate_id")),
        mode="PAPER",
        tradingsymbol=_str_or_none(intent.get("tradingsymbol") or intent.get("symbol")),
        transaction_type=_normalized_choice(intent.get("transaction_type"), SUPPORTED_TRANSACTION_TYPES),
        quantity=_int_or_none(intent.get("quantity")),
        order_type=_normalized_choice(intent.get("order_type"), SUPPORTED_ORDER_TYPES),
        product=_normalized_choice(intent.get("product"), SUPPORTED_PRODUCTS),
        price=_float_or_none(intent.get("price")),
        trigger_price=_float_or_none(intent.get("trigger_price")),
        created_at_epoch=ts_epoch,
        intent_snapshot=dict(intent),
    )
    return PaperBrokerExecutionResult(accepted=True, ack=ack, warnings=warnings)


def validate_paper_order_intent(
    *,
    intent: dict[str, Any] | None,
    broker_client: Any | None = None,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if broker_client is not None:
        blockers.append("REAL_BROKER_CLIENT_FORBIDDEN_IN_PAPER")

    if not isinstance(intent, dict) or not intent:
        blockers.append("ORDER_INTENT_REQUIRED")
        return _dedupe(blockers), warnings

    if intent.get("mode") != "PAPER":
        blockers.append("PAPER_MODE_REQUIRED")
    if intent.get("is_order_action") is not False:
        blockers.append("INTENT_ORDER_FLAG_UNSAFE")
    if intent.get("broker_api_called") is not False:
        blockers.append("INTENT_BROKER_API_FLAG_UNSAFE")
    if intent.get("real_order_id") is not None:
        blockers.append("INTENT_REAL_ORDER_ID_FORBIDDEN")
    if intent.get("requires_broker_adapter") is not False:
        blockers.append("INTENT_REQUIRES_BROKER_ADAPTER_UNSAFE")

    if intent.get("intent_id") in (None, ""):
        blockers.append("INTENT_ID_REQUIRED")
    if intent.get("candidate_id") in (None, ""):
        blockers.append("CANDIDATE_ID_REQUIRED")

    transaction_type = _normalized_choice(intent.get("transaction_type"), SUPPORTED_TRANSACTION_TYPES)
    if transaction_type is None:
        blockers.append("TRANSACTION_TYPE_REQUIRED_OR_UNSUPPORTED")

    quantity = _int_or_none(intent.get("quantity"))
    if quantity is None or quantity <= 0:
        blockers.append("POSITIVE_QUANTITY_REQUIRED")

    order_type = _normalized_choice(intent.get("order_type"), SUPPORTED_ORDER_TYPES)
    if order_type is None:
        blockers.append("ORDER_TYPE_REQUIRED_OR_UNSUPPORTED")

    product = _normalized_choice(intent.get("product"), SUPPORTED_PRODUCTS)
    if product is None:
        blockers.append("PRODUCT_REQUIRED_OR_UNSUPPORTED")

    if order_type == "LIMIT" and _float_or_none(intent.get("price")) is None:
        blockers.append("LIMIT_PRICE_REQUIRED")

    if order_type in {"SL", "SL-M"} and _float_or_none(intent.get("trigger_price")) is None:
        blockers.append("TRIGGER_PRICE_REQUIRED")

    return _dedupe(blockers), _dedupe(warnings)


def _stable_paper_order_id(intent: dict[str, Any], ts_epoch: float | None) -> str:
    seed = "|".join(
        [
            str(intent.get("intent_id") or ""),
            str(intent.get("candidate_id") or ""),
            str(intent.get("mode") or ""),
            str(ts_epoch or ""),
        ]
    )
    return f"paper-{sha256(seed.encode('utf-8')).hexdigest()[:16]}"


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

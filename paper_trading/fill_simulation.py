from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from paper_trading.lifecycle import (
    TERMINAL_PAPER_ORDER_STATES,
    PaperOrderLifecycleEvent,
    build_paper_order_lifecycle_event,
)


PAPER_FILL_SIMULATION_SCHEMA_VERSION = "1.0"
CONTROLLED_QUOTE_SOURCES = {"CONTROLLED_QUOTE", "TEST_QUOTE", "SIMULATED_QUOTE", "PAPER_QUOTE"}
FILLABLE_PREVIOUS_STATUSES = {"OPEN", "PARTIALLY_FILLED"}


class PaperFillSimulationStatus(StrEnum):
    FULL_FILL = "FULL_FILL"
    PARTIAL_FILL = "PARTIAL_FILL"
    NO_FILL = "NO_FILL"
    REJECTED_FILL = "REJECTED_FILL"
    EXPIRED_FILL = "EXPIRED_FILL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PaperFillSimulationResult:
    simulated: bool
    status: PaperFillSimulationStatus
    lifecycle_event: dict[str, Any] | None = None
    fill_quantity: int = 0
    cumulative_filled_quantity: int = 0
    remaining_quantity: int | None = None
    fill_price: float | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: str = PAPER_FILL_SIMULATION_SCHEMA_VERSION

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
            "simulation_type": "PAPER_FILL_SIMULATION_ENGINE",
            "simulated": self.simulated,
            "status": self.status.value,
            "lifecycle_event": dict(self.lifecycle_event) if self.lifecycle_event else None,
            "fill_quantity": self.fill_quantity,
            "cumulative_filled_quantity": self.cumulative_filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "fill_price": self.fill_price,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "paper_only": self.paper_only,
            "is_order_action": self.is_order_action,
            "broker_api_called": self.broker_api_called,
            "real_order_id": self.real_order_id,
        }


def paper_fill_simulation_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": PAPER_FILL_SIMULATION_SCHEMA_VERSION,
        "simulation_type": "PAPER_FILL_SIMULATION_ENGINE",
        "consumes": ["PAPER_ORDER_INTENT", "PAPER_ORDER_LIFECYCLE_EVENT", "CONTROLLED_QUOTE"],
        "statuses": [status.value for status in PaperFillSimulationStatus],
        "controlled_quote_sources": sorted(CONTROLLED_QUOTE_SOURCES),
        "required_result_keys": [
            "schema_version",
            "simulation_type",
            "simulated",
            "status",
            "lifecycle_event",
            "fill_quantity",
            "cumulative_filled_quantity",
            "remaining_quantity",
            "fill_price",
            "blockers",
            "warnings",
            "evidence",
            "paper_only",
            "is_order_action",
            "broker_api_called",
            "real_order_id",
        ],
        "safe_flags": {
            "paper_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
        "scope_boundary": [
            "paper_only",
            "controlled_quote_inputs_only",
            "no_broker_execution",
            "no_live_orders",
            "no_pnl",
            "no_slippage_tracker",
            "no_ui",
        ],
    }


def simulate_paper_fill(
    *,
    intent: dict[str, Any] | None,
    previous_event: dict[str, Any] | PaperOrderLifecycleEvent | None,
    quote: dict[str, Any] | None,
    ts_epoch: float | None = None,
    now_epoch: float | None = None,
    max_quote_age_sec: float = 5.0,
) -> PaperFillSimulationResult:
    previous_payload = _event_payload(previous_event)
    quote_payload = quote if isinstance(quote, dict) else {}
    blockers, warnings = validate_paper_fill_simulation_inputs(
        intent=intent,
        previous_event=previous_payload,
        quote=quote_payload,
        now_epoch=now_epoch,
        max_quote_age_sec=max_quote_age_sec,
    )
    evidence = _simulation_evidence(
        intent=intent,
        previous_event=previous_payload,
        quote=quote_payload,
        now_epoch=now_epoch,
        max_quote_age_sec=max_quote_age_sec,
    )
    if blockers:
        return PaperFillSimulationResult(
            simulated=False,
            status=PaperFillSimulationStatus.BLOCKED,
            blockers=blockers,
            warnings=warnings,
            evidence=evidence,
        )

    intent_payload = dict(intent or {})
    quantity = _int_or_none(intent_payload.get("quantity")) or 0
    previous_filled = _int_or_none(previous_payload.get("filled_quantity")) or 0
    remaining_before = max(quantity - previous_filled, 0)

    if _is_expired(intent_payload, quote_payload, now_epoch):
        return _terminal_simulation_result(
            status=PaperFillSimulationStatus.EXPIRED_FILL,
            lifecycle_status="EXPIRED",
            intent=intent_payload,
            previous_event=previous_payload,
            quote=quote_payload,
            ts_epoch=ts_epoch,
            reason="paper fill simulation expired from controlled input",
            previous_filled=previous_filled,
            remaining_before=remaining_before,
            warnings=warnings,
            evidence=evidence,
        )

    if _is_rejected(quote_payload):
        return _terminal_simulation_result(
            status=PaperFillSimulationStatus.REJECTED_FILL,
            lifecycle_status="REJECTED",
            intent=intent_payload,
            previous_event=previous_payload,
            quote=quote_payload,
            ts_epoch=ts_epoch,
            reason=str(quote_payload.get("reject_reason") or "paper fill simulation rejected from controlled input"),
            previous_filled=previous_filled,
            remaining_before=remaining_before,
            warnings=warnings,
            evidence=evidence,
        )

    fill_price = _resolved_fill_price(intent_payload, quote_payload)
    if fill_price is None:
        return PaperFillSimulationResult(
            simulated=True,
            status=PaperFillSimulationStatus.NO_FILL,
            fill_quantity=0,
            cumulative_filled_quantity=previous_filled,
            remaining_quantity=remaining_before,
            fill_price=None,
            warnings=_dedupe(warnings + ["NO_MARKETABLE_PRICE_FROM_CONTROLLED_QUOTE"]),
            evidence=evidence,
        )

    available_quantity = _available_quantity(quote_payload, remaining_before)
    if available_quantity <= 0:
        return PaperFillSimulationResult(
            simulated=True,
            status=PaperFillSimulationStatus.NO_FILL,
            fill_quantity=0,
            cumulative_filled_quantity=previous_filled,
            remaining_quantity=remaining_before,
            fill_price=fill_price,
            warnings=_dedupe(warnings + ["NO_CONTROLLED_QUOTE_LIQUIDITY"]),
            evidence=evidence,
        )

    fill_quantity = min(available_quantity, remaining_before)
    cumulative = previous_filled + fill_quantity
    remaining_after = max(quantity - cumulative, 0)
    lifecycle_status = "FILLED" if remaining_after == 0 else "PARTIALLY_FILLED"
    lifecycle = build_paper_order_lifecycle_event(
        intent=intent_payload,
        previous_event=previous_payload,
        requested_status=lifecycle_status,
        filled_quantity=cumulative,
        average_fill_price=fill_price,
        ts_epoch=ts_epoch,
        reason="paper fill simulation from controlled quote",
    )
    if not lifecycle.created:
        return PaperFillSimulationResult(
            simulated=False,
            status=PaperFillSimulationStatus.BLOCKED,
            blockers=_dedupe(lifecycle.blockers),
            warnings=_dedupe(warnings + lifecycle.warnings),
            evidence=evidence,
        )

    return PaperFillSimulationResult(
        simulated=True,
        status=PaperFillSimulationStatus.FULL_FILL if lifecycle_status == "FILLED" else PaperFillSimulationStatus.PARTIAL_FILL,
        lifecycle_event=lifecycle.to_dict()["event"],
        fill_quantity=fill_quantity,
        cumulative_filled_quantity=cumulative,
        remaining_quantity=remaining_after,
        fill_price=fill_price,
        warnings=warnings,
        evidence=evidence,
    )


def validate_paper_fill_simulation_inputs(
    *,
    intent: dict[str, Any] | None,
    previous_event: dict[str, Any] | None,
    quote: dict[str, Any] | None,
    now_epoch: float | None = None,
    max_quote_age_sec: float = 5.0,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    intent_payload = intent if isinstance(intent, dict) else {}
    event_payload = previous_event if isinstance(previous_event, dict) else {}
    quote_payload = quote if isinstance(quote, dict) else {}

    if not intent_payload:
        blockers.append("PAPER_INTENT_REQUIRED")
    else:
        if intent_payload.get("intent_type") != "PAPER_ORDER_INTENT":
            blockers.append("PAPER_INTENT_TYPE_REQUIRED")
        if intent_payload.get("paper_only") is not True:
            blockers.append("PAPER_INTENT_NOT_PAPER_ONLY")
        if intent_payload.get("is_order_action") is not False:
            blockers.append("PAPER_INTENT_ORDER_FLAG_UNSAFE")
        if intent_payload.get("broker_api_called") is not False:
            blockers.append("PAPER_INTENT_BROKER_API_CALLED")
        if intent_payload.get("real_order_id") not in (None, ""):
            blockers.append("PAPER_INTENT_REAL_ORDER_ID_PRESENT")
        if (_int_or_none(intent_payload.get("quantity")) or 0) <= 0:
            blockers.append("PAPER_ORDER_QUANTITY_REQUIRED")

    if not event_payload:
        blockers.append("PAPER_ORDER_LIFECYCLE_EVENT_REQUIRED")
    else:
        if event_payload.get("event_type") != "PAPER_ORDER_LIFECYCLE_EVENT":
            blockers.append("PAPER_ORDER_LIFECYCLE_EVENT_TYPE_REQUIRED")
        if event_payload.get("paper_only") is not True:
            blockers.append("PAPER_ORDER_LIFECYCLE_NOT_PAPER_ONLY")
        if event_payload.get("is_order_action") is not False:
            blockers.append("PAPER_ORDER_LIFECYCLE_ORDER_FLAG_UNSAFE")
        if event_payload.get("broker_api_called") is not False:
            blockers.append("PAPER_ORDER_LIFECYCLE_BROKER_API_CALLED")
        if event_payload.get("real_order_id") not in (None, ""):
            blockers.append("PAPER_ORDER_LIFECYCLE_REAL_ORDER_ID_PRESENT")
        previous_status = str(event_payload.get("status") or "").upper()
        if previous_status in TERMINAL_PAPER_ORDER_STATES:
            blockers.append("PAPER_ORDER_ALREADY_TERMINAL")
        elif previous_status not in FILLABLE_PREVIOUS_STATUSES:
            blockers.append("PAPER_ORDER_NOT_OPEN_FOR_FILL_SIMULATION")

    if intent_payload and event_payload:
        if str(intent_payload.get("paper_order_intent_id")) != str(event_payload.get("paper_order_intent_id")):
            blockers.append("PAPER_INTENT_LIFECYCLE_MISMATCH")
        if str(intent_payload.get("candidate_id")) != str(event_payload.get("candidate_id")):
            blockers.append("PAPER_CANDIDATE_LIFECYCLE_MISMATCH")

    if not quote_payload:
        blockers.append("CONTROLLED_QUOTE_REQUIRED")
    else:
        quote_source = str(quote_payload.get("source") or "").upper()
        if quote_source not in CONTROLLED_QUOTE_SOURCES:
            blockers.append("CONTROLLED_QUOTE_SOURCE_REQUIRED")
        if quote_payload.get("is_order_action") is not False:
            blockers.append("CONTROLLED_QUOTE_ORDER_FLAG_UNSAFE")
        if quote_payload.get("broker_api_called") is True:
            blockers.append("CONTROLLED_QUOTE_BROKER_API_CALLED")
        if quote_payload.get("real_order_id") not in (None, ""):
            blockers.append("CONTROLLED_QUOTE_REAL_ORDER_ID_PRESENT")
        age = _quote_age_sec(quote_payload, now_epoch)
        if age is not None and age > max_quote_age_sec:
            blockers.append("CONTROLLED_QUOTE_STALE")
        elif age is None:
            warnings.append("CONTROLLED_QUOTE_AGE_UNAVAILABLE")

    return _dedupe(blockers), _dedupe(warnings)


def _terminal_simulation_result(
    *,
    status: PaperFillSimulationStatus,
    lifecycle_status: str,
    intent: dict[str, Any],
    previous_event: dict[str, Any],
    quote: dict[str, Any],
    ts_epoch: float | None,
    reason: str,
    previous_filled: int,
    remaining_before: int,
    warnings: list[str],
    evidence: dict[str, Any],
) -> PaperFillSimulationResult:
    lifecycle = build_paper_order_lifecycle_event(
        intent=intent,
        previous_event=previous_event,
        requested_status=lifecycle_status,
        filled_quantity=0,
        ts_epoch=ts_epoch,
        reason=reason,
    )
    if not lifecycle.created:
        return PaperFillSimulationResult(
            simulated=False,
            status=PaperFillSimulationStatus.BLOCKED,
            blockers=_dedupe(lifecycle.blockers),
            warnings=_dedupe(warnings + lifecycle.warnings),
            evidence=evidence,
        )
    return PaperFillSimulationResult(
        simulated=True,
        status=status,
        lifecycle_event=lifecycle.to_dict()["event"],
        fill_quantity=0,
        cumulative_filled_quantity=previous_filled,
        remaining_quantity=remaining_before,
        fill_price=None,
        warnings=warnings,
        evidence=dict(evidence, quote_status=quote.get("status")),
    )


def _resolved_fill_price(intent: dict[str, Any], quote: dict[str, Any]) -> float | None:
    transaction_type = str(intent.get("transaction_type") or "").upper()
    order_type = str(intent.get("order_type") or "LIMIT").upper()
    limit_price = _float_or_none(intent.get("price"))
    bid = _float_or_none(quote.get("bid") or quote.get("best_bid"))
    ask = _float_or_none(quote.get("ask") or quote.get("best_ask"))
    last = _float_or_none(quote.get("last") or quote.get("ltp") or quote.get("mark"))

    if transaction_type == "BUY":
        executable_price = ask or last
        if executable_price is None:
            return None
        if order_type == "MARKET" or limit_price is None:
            return executable_price
        return executable_price if executable_price <= limit_price else None
    if transaction_type == "SELL":
        executable_price = bid or last
        if executable_price is None:
            return None
        if order_type == "MARKET" or limit_price is None:
            return executable_price
        return executable_price if executable_price >= limit_price else None
    return None


def _available_quantity(quote: dict[str, Any], remaining_before: int) -> int:
    for key in ("available_quantity", "available_qty", "fillable_quantity", "fillable_qty", "size", "quantity"):
        value = _int_or_none(quote.get(key))
        if value is not None:
            return max(value, 0)
    return remaining_before


def _is_rejected(quote: dict[str, Any]) -> bool:
    status = str(quote.get("status") or "").upper()
    return quote.get("reject") is True or quote.get("rejected") is True or status in {"REJECTED", "REJECTED_FILL"}


def _is_expired(intent: dict[str, Any], quote: dict[str, Any], now_epoch: float | None) -> bool:
    status = str(quote.get("status") or "").upper()
    if quote.get("expired") is True or status in {"EXPIRED", "EXPIRED_FILL"}:
        return True
    expiry_epoch = _float_or_none(quote.get("order_expiry_epoch") or intent.get("order_expiry_epoch"))
    return bool(expiry_epoch is not None and now_epoch is not None and now_epoch >= expiry_epoch)


def _simulation_evidence(
    *,
    intent: dict[str, Any] | None,
    previous_event: dict[str, Any] | None,
    quote: dict[str, Any] | None,
    now_epoch: float | None,
    max_quote_age_sec: float,
) -> dict[str, Any]:
    intent_payload = intent if isinstance(intent, dict) else {}
    event_payload = previous_event if isinstance(previous_event, dict) else {}
    quote_payload = quote if isinstance(quote, dict) else {}
    return {
        "paper_order_intent_id": intent_payload.get("paper_order_intent_id"),
        "candidate_id": intent_payload.get("candidate_id"),
        "previous_status": event_payload.get("status"),
        "quote_source": quote_payload.get("source"),
        "quote_ts_epoch": quote_payload.get("ts_epoch"),
        "quote_age_sec": _quote_age_sec(quote_payload, now_epoch),
        "max_quote_age_sec": max_quote_age_sec,
        "controlled_quote_only": True,
        "paper_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
    }


def _quote_age_sec(quote: dict[str, Any], now_epoch: float | None) -> float | None:
    quote_ts = _float_or_none(quote.get("ts_epoch") or quote.get("quote_ts_epoch"))
    if quote_ts is None or now_epoch is None:
        return None
    return max(float(now_epoch) - quote_ts, 0.0)


def _event_payload(previous_event: dict[str, Any] | PaperOrderLifecycleEvent | None) -> dict[str, Any] | None:
    if isinstance(previous_event, PaperOrderLifecycleEvent):
        return previous_event.to_dict()
    return previous_event if isinstance(previous_event, dict) else None


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

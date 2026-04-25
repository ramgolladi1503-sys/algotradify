import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from kiteconnect import KiteConnect


class ExecutionRequest(BaseModel):
    tradingsymbol: str
    exchange: str = "NFO"
    transaction_type: str = "BUY"
    quantity: int = Field(gt=0)
    product: str = "MIS"
    order_type: str = "MARKET"
    variety: str = "regular"
    validity: str = "DAY"
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    tag: Optional[str] = None
    dry_run: Optional[bool] = None


class ExecutionResult(BaseModel):
    accepted: bool
    dry_run: bool
    order_id: Optional[str] = None
    client_order_id: str
    status: str
    reason: Optional[str] = None
    request: ExecutionRequest
    submitted_at: str


class FillRecord(BaseModel):
    order_id: str
    tradingsymbol: str
    transaction_type: str
    filled_quantity: int
    average_price: float
    status: str
    exchange: str
    product: str
    filled_at: str
    client_order_id: Optional[str] = None
    partial: bool = False
    original_quantity: Optional[int] = None


class CancelResult(BaseModel):
    order_id: str
    accepted: bool
    status: str
    reason: Optional[str] = None
    cancelled_at: str


class KiteExecutionEngine:
    def __init__(self):
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")
        self.live_enabled = os.getenv("LIVE_ORDER_ENABLED", "false").lower() == "true"
        self.max_order_qty = int(os.getenv("MAX_ORDER_QTY", "1800"))
        self.order_timeout_sec = int(os.getenv("ORDER_TIMEOUT_SEC", "45"))
        self.audit: list[dict] = []
        self.pending: dict[str, ExecutionResult] = {}
        self.fills: dict[str, FillRecord] = {}
        self.cancelled: dict[str, CancelResult] = {}
        self.kite = None
        if self.api_key and self.access_token:
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)

    def place_order(self, req: ExecutionRequest) -> ExecutionResult:
        client_order_id = req.tag or f"alg-{uuid.uuid4().hex[:12]}"
        dry_run = req.dry_run if req.dry_run is not None else not self.live_enabled
        submitted_at = datetime.now(timezone.utc).isoformat()

        safety_reason = self._safety_check(req)
        if safety_reason:
            result = ExecutionResult(
                accepted=False,
                dry_run=True,
                client_order_id=client_order_id,
                status="REJECTED_BY_LOCAL_SAFETY",
                reason=safety_reason,
                request=req,
                submitted_at=submitted_at,
            )
            self._audit(result)
            return result

        if dry_run:
            result = ExecutionResult(
                accepted=True,
                dry_run=True,
                order_id=f"DRYRUN-{client_order_id}",
                client_order_id=client_order_id,
                status="DRY_RUN_ACCEPTED",
                reason="LIVE_ORDER_ENABLED is false or request dry_run=true",
                request=req,
                submitted_at=submitted_at,
            )
            self._audit(result)
            self.pending[result.order_id] = result
            self.fills[result.order_id] = FillRecord(
                order_id=result.order_id,
                tradingsymbol=req.tradingsymbol,
                transaction_type=req.transaction_type,
                filled_quantity=req.quantity,
                average_price=req.price or 0.0,
                status="COMPLETE",
                exchange=req.exchange,
                product=req.product,
                filled_at=submitted_at,
                client_order_id=client_order_id,
                partial=False,
                original_quantity=req.quantity,
            )
            return result

        if not self.kite:
            result = ExecutionResult(
                accepted=False,
                dry_run=False,
                client_order_id=client_order_id,
                status="REJECTED_NO_KITE_SESSION",
                reason="Missing Kite credentials/session",
                request=req,
                submitted_at=submitted_at,
            )
            self._audit(result)
            return result

        try:
            order_id = self.kite.place_order(
                variety=req.variety,
                exchange=req.exchange,
                tradingsymbol=req.tradingsymbol,
                transaction_type=req.transaction_type,
                quantity=req.quantity,
                product=req.product,
                order_type=req.order_type,
                price=req.price,
                trigger_price=req.trigger_price,
                validity=req.validity,
                tag=client_order_id[:20],
            )
            result = ExecutionResult(
                accepted=True,
                dry_run=False,
                order_id=str(order_id),
                client_order_id=client_order_id,
                status="SUBMITTED_TO_KITE",
                reason="Order submitted; verify order history for final status",
                request=req,
                submitted_at=submitted_at,
            )
            self.pending[result.order_id] = result
        except Exception as exc:
            result = ExecutionResult(
                accepted=False,
                dry_run=False,
                client_order_id=client_order_id,
                status="KITE_ORDER_FAILED",
                reason=str(exc),
                request=req,
                submitted_at=submitted_at,
            )

        self._audit(result)
        return result

    def sync_fills(self) -> list[FillRecord]:
        if not self.pending:
            return []

        if not self.kite:
            fills = list(self.fills.values())
            for f in fills:
                self.pending.pop(f.order_id, None)
            return fills

        try:
            orders = self.kite.orders()
        except Exception as exc:
            self.audit.append({"status": "ORDER_SYNC_FAILED", "reason": str(exc), "at": self._now()})
            return []

        new_fills = []
        by_order_id = {str(o.get("order_id")): o for o in orders}

        for order_id, submitted in list(self.pending.items()):
            if order_id in self.fills:
                new_fills.append(self.fills[order_id])
                self.pending.pop(order_id, None)
                continue

            order = by_order_id.get(str(order_id))
            if not order:
                if self._is_timed_out(submitted):
                    self.cancel_order(order_id, reason="missing_order_timeout")
                continue

            status = str(order.get("status") or "UNKNOWN").upper()
            filled_qty = int(order.get("filled_quantity") or 0)
            total_qty = int(order.get("quantity") or submitted.request.quantity or 0)
            avg_price = float(order.get("average_price") or order.get("price") or 0.0)

            if filled_qty > 0 and avg_price > 0:
                partial = filled_qty < total_qty or status not in {"COMPLETE"}
                fill = FillRecord(
                    order_id=str(order_id),
                    tradingsymbol=str(order.get("tradingsymbol") or submitted.request.tradingsymbol),
                    transaction_type=str(order.get("transaction_type") or submitted.request.transaction_type),
                    filled_quantity=filled_qty,
                    average_price=avg_price,
                    status="PARTIAL" if partial else "COMPLETE",
                    exchange=str(order.get("exchange") or submitted.request.exchange),
                    product=str(order.get("product") or submitted.request.product),
                    filled_at=self._now(),
                    client_order_id=submitted.client_order_id,
                    partial=partial,
                    original_quantity=total_qty,
                )
                self.fills[order_id] = fill
                new_fills.append(fill)

                if partial and self._is_timed_out(submitted):
                    self.cancel_order(order_id, reason="partial_fill_timeout")
                    self.pending.pop(order_id, None)
                elif not partial:
                    self.pending.pop(order_id, None)

            elif status in {"REJECTED", "CANCELLED"}:
                self.audit.append({"status": status, "order_id": order_id, "order": order, "at": self._now()})
                self.pending.pop(order_id, None)
            elif self._is_timed_out(submitted):
                self.cancel_order(order_id, reason="order_timeout")

        return new_fills

    def cancel_order(self, order_id: str, reason: str = "manual_cancel") -> CancelResult:
        cancelled_at = self._now()
        submitted = self.pending.get(order_id)

        if order_id.startswith("DRYRUN-") or not self.kite:
            result = CancelResult(order_id=order_id, accepted=True, status="LOCAL_CANCELLED", reason=reason, cancelled_at=cancelled_at)
            self.cancelled[order_id] = result
            self.pending.pop(order_id, None)
            self.audit.append(result.model_dump())
            return result

        try:
            variety = submitted.request.variety if submitted else "regular"
            self.kite.cancel_order(variety=variety, order_id=order_id)
            result = CancelResult(order_id=order_id, accepted=True, status="CANCEL_REQUESTED", reason=reason, cancelled_at=cancelled_at)
            self.pending.pop(order_id, None)
        except Exception as exc:
            result = CancelResult(order_id=order_id, accepted=False, status="CANCEL_FAILED", reason=str(exc), cancelled_at=cancelled_at)

        self.cancelled[order_id] = result
        self.audit.append(result.model_dump())
        return result

    def pending_orders(self):
        return {k: v.model_dump() for k, v in self.pending.items()}

    def filled_orders(self):
        return {k: v.model_dump() for k, v in self.fills.items()}

    def cancelled_orders(self):
        return {k: v.model_dump() for k, v in self.cancelled.items()}

    def orders(self):
        if not self.kite:
            return {"error": "missing_kite_session"}
        return self.kite.orders()

    def trades(self):
        if not self.kite:
            return {"error": "missing_kite_session"}
        return self.kite.trades()

    def state(self) -> dict:
        return {
            "live_enabled": self.live_enabled,
            "has_kite_session": self.kite is not None,
            "max_order_qty": self.max_order_qty,
            "order_timeout_sec": self.order_timeout_sec,
            "pending_count": len(self.pending),
            "fill_count": len(self.fills),
            "cancelled_count": len(self.cancelled),
            "audit_count": len(self.audit),
            "last_audit": self.audit[-10:],
        }

    def _safety_check(self, req: ExecutionRequest) -> Optional[str]:
        if req.quantity <= 0:
            return "quantity_must_be_positive"
        if req.quantity > self.max_order_qty:
            return "quantity_exceeds_max_order_qty"
        if req.transaction_type not in {"BUY", "SELL"}:
            return "invalid_transaction_type"
        if req.exchange not in {"NFO", "NSE", "BSE", "BFO"}:
            return "invalid_exchange"
        if req.order_type not in {"MARKET", "LIMIT", "SL", "SL-M"}:
            return "invalid_order_type"
        if req.order_type == "LIMIT" and req.price is None:
            return "limit_order_requires_price"
        if req.order_type in {"SL", "SL-M"} and req.trigger_price is None:
            return "stop_order_requires_trigger_price"
        return None

    def _is_timed_out(self, submitted: ExecutionResult) -> bool:
        submitted_at = datetime.fromisoformat(submitted.submitted_at.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - submitted_at).total_seconds()
        return age >= self.order_timeout_sec

    def _audit(self, result: ExecutionResult):
        self.audit.append(result.model_dump())
        self.audit = self.audit[-500:]

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

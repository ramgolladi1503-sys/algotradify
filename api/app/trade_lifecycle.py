from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid


class Position(BaseModel):
    trade_id: str
    symbol: str
    side: str
    quantity: int
    entry_price: float
    stop_loss: float
    target: float
    trailing_stop: float | None = None
    opened_at: str
    max_hold_minutes: int = 45
    status: str = "OPEN"
    exit_price: float | None = None
    exit_reason: str | None = None
    closed_at: str | None = None
    pnl: float = 0.0
    unrealized_pnl: float = 0.0


class LifecycleEngine:
    def __init__(self):
        self.positions: dict[str, Position] = {}
        self.closed: list[Position] = []

    def open_position(self, candidate, snapshot, quantity: int) -> Position:
        if quantity <= 0:
            raise ValueError("quantity_must_be_positive")
        if not snapshot.ltp or snapshot.ltp <= 0:
            raise ValueError("entry_ltp_missing")

        entry = float(snapshot.ltp)
        risk_per_unit = max(entry * 0.20, 1.0)
        if candidate.side.upper() == "BUY":
            stop = max(entry - risk_per_unit, 0.05)
            target = entry + (risk_per_unit * 2)
        else:
            stop = entry + risk_per_unit
            target = max(entry - (risk_per_unit * 2), 0.05)

        pos = Position(
            trade_id=str(uuid.uuid4()),
            symbol=candidate.symbol,
            side=candidate.side.upper(),
            quantity=quantity,
            entry_price=round(entry, 2),
            stop_loss=round(stop, 2),
            target=round(target, 2),
            trailing_stop=None,
            opened_at=self._now(),
        )
        self.positions[pos.trade_id] = pos
        return pos

    def mark_to_market(self, snapshots: list) -> list[Position]:
        by_symbol = {s.symbol: s for s in snapshots}
        updated = []
        for trade_id, pos in list(self.positions.items()):
            snap = by_symbol.get(pos.symbol)
            if not snap or not snap.ltp:
                continue
            self._update_position(pos, float(snap.ltp))
            exit_reason = self._exit_reason(pos, float(snap.ltp))
            if exit_reason:
                self.close_position(trade_id, float(snap.ltp), exit_reason)
            updated.append(pos)
        return updated

    def close_position(self, trade_id: str, price: float, reason: str) -> Position:
        pos = self.positions.pop(trade_id)
        pnl = self._pnl(pos, price)
        pos.status = "CLOSED"
        pos.exit_price = round(price, 2)
        pos.exit_reason = reason
        pos.closed_at = self._now()
        pos.pnl = round(pnl, 2)
        pos.unrealized_pnl = 0.0
        self.closed.append(pos)
        return pos

    def open_positions(self) -> list[Position]:
        return list(self.positions.values())

    def closed_trades(self) -> list[Position]:
        return self.closed[-200:]

    def summary(self) -> dict:
        realized = sum(p.pnl for p in self.closed)
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        return {
            "open_count": len(self.positions),
            "closed_count": len(self.closed),
            "realized_pnl": round(realized, 2),
            "unrealized_pnl": round(unrealized, 2),
            "total_pnl": round(realized + unrealized, 2),
        }

    def _update_position(self, pos: Position, ltp: float):
        pos.unrealized_pnl = round(self._pnl(pos, ltp), 2)
        trail_gap = max(pos.entry_price * 0.12, 1.0)
        if pos.side == "BUY" and ltp > pos.entry_price:
            new_trail = max(pos.trailing_stop or pos.stop_loss, ltp - trail_gap)
            pos.trailing_stop = round(new_trail, 2)
        elif pos.side == "SELL" and ltp < pos.entry_price:
            new_trail = min(pos.trailing_stop or pos.stop_loss, ltp + trail_gap)
            pos.trailing_stop = round(new_trail, 2)

    def _exit_reason(self, pos: Position, ltp: float) -> str | None:
        stop = pos.trailing_stop or pos.stop_loss
        if pos.side == "BUY":
            if ltp <= stop:
                return "stop_loss_hit"
            if ltp >= pos.target:
                return "target_hit"
        else:
            if ltp >= stop:
                return "stop_loss_hit"
            if ltp <= pos.target:
                return "target_hit"

        opened = datetime.fromisoformat(pos.opened_at.replace("Z", "+00:00"))
        age_min = (datetime.now(timezone.utc) - opened).total_seconds() / 60
        if age_min >= pos.max_hold_minutes:
            return "time_exit"
        return None

    def _pnl(self, pos: Position, price: float) -> float:
        if pos.side == "BUY":
            return (price - pos.entry_price) * pos.quantity
        return (pos.entry_price - price) * pos.quantity

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

from pydantic import BaseModel, Field


class SizingDecision(BaseModel):
    allowed: bool
    quantity: int = 0
    lots: int = 0
    risk_amount: float = 0.0
    notional: float = 0.0
    risk_per_unit: float = 0.0
    max_loss_pct: float = 0.0
    reason: str | None = None


class PositionSizingEngine:
    def __init__(
        self,
        capital: float = 100000.0,
        base_risk_pct: float = 0.005,
        max_risk_pct: float = 0.015,
        max_notional_pct: float = 0.25,
        default_lot_size: int = 50,
    ):
        self.capital = capital
        self.base_risk_pct = base_risk_pct
        self.max_risk_pct = max_risk_pct
        self.max_notional_pct = max_notional_pct
        self.default_lot_size = default_lot_size

    def size(self, candidate, snapshot, lot_size: int | None = None) -> SizingDecision:
        lot = lot_size or self.default_lot_size

        if not candidate.executable:
            return SizingDecision(allowed=False, reason="candidate_not_executable")

        if not snapshot.ltp or snapshot.ltp <= 0:
            return SizingDecision(allowed=False, reason="ltp_missing")

        confidence_factor = max(0.5, min(1.5, candidate.confidence + candidate.score))
        liquidity_factor = max(0.25, min(1.0, candidate.liquidity))
        risk_pct = min(self.max_risk_pct, self.base_risk_pct * confidence_factor * liquidity_factor)
        risk_amount = self.capital * risk_pct

        # conservative initial risk proxy: 20% of premium or 1 point minimum
        risk_per_unit = max(snapshot.ltp * 0.20, 1.0)
        raw_qty = int(risk_amount / risk_per_unit)
        lots = raw_qty // lot
        quantity = lots * lot

        notional = quantity * snapshot.ltp
        max_notional = self.capital * self.max_notional_pct

        if quantity <= 0:
            return SizingDecision(allowed=False, reason="size_below_one_lot")

        if notional > max_notional:
            max_qty = int(max_notional / snapshot.ltp)
            lots = max_qty // lot
            quantity = lots * lot
            notional = quantity * snapshot.ltp

        if quantity <= 0:
            return SizingDecision(allowed=False, reason="notional_cap_blocks_trade")

        return SizingDecision(
            allowed=True,
            quantity=quantity,
            lots=lots,
            risk_amount=round(risk_amount, 2),
            notional=round(notional, 2),
            risk_per_unit=round(risk_per_unit, 2),
            max_loss_pct=round((risk_amount / self.capital) * 100, 3),
        )

    def state(self) -> dict:
        return {
            "capital": self.capital,
            "base_risk_pct": self.base_risk_pct,
            "max_risk_pct": self.max_risk_pct,
            "max_notional_pct": self.max_notional_pct,
            "default_lot_size": self.default_lot_size,
        }

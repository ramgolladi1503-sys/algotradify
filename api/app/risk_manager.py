from pydantic import BaseModel, Field


class RiskDecision(BaseModel):
    allowed: bool
    reason: str | None = None
    reserved_risk: float = 0.0
    projected_notional: float = 0.0


class CapitalManager:
    def __init__(
        self,
        starting_capital: float = 100000.0,
        max_open_positions: int = 3,
        max_positions_per_symbol: int = 1,
        max_total_risk_pct: float = 0.03,
        max_total_notional_pct: float = 0.60,
        max_daily_loss_pct: float = 0.03,
    ):
        self.starting_capital = starting_capital
        self.current_capital = starting_capital
        self.realized_pnl = 0.0
        self.reserved_risk = 0.0
        self.reserved_notional = 0.0
        self.max_open_positions = max_open_positions
        self.max_positions_per_symbol = max_positions_per_symbol
        self.max_total_risk_pct = max_total_risk_pct
        self.max_total_notional_pct = max_total_notional_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.risk_halt = False
        self.risk_halt_reason = None

    def approve_entry(self, candidate, sizing, open_positions: list) -> RiskDecision:
        if self.risk_halt:
            return RiskDecision(allowed=False, reason=self.risk_halt_reason or "risk_halt")

        if not sizing.allowed:
            return RiskDecision(allowed=False, reason=sizing.reason or "sizing_blocked")

        if len(open_positions) >= self.max_open_positions:
            return RiskDecision(allowed=False, reason="max_open_positions_reached")

        same_symbol = [p for p in open_positions if p.symbol == candidate.symbol]
        if len(same_symbol) >= self.max_positions_per_symbol:
            return RiskDecision(allowed=False, reason="max_positions_per_symbol_reached")

        projected_risk = self.reserved_risk + sizing.risk_amount
        projected_notional = self.reserved_notional + sizing.notional

        if projected_risk > self.current_capital * self.max_total_risk_pct:
            return RiskDecision(
                allowed=False,
                reason="portfolio_risk_limit_exceeded",
                reserved_risk=round(self.reserved_risk, 2),
                projected_notional=round(projected_notional, 2),
            )

        if projected_notional > self.current_capital * self.max_total_notional_pct:
            return RiskDecision(
                allowed=False,
                reason="portfolio_notional_limit_exceeded",
                reserved_risk=round(projected_risk, 2),
                projected_notional=round(projected_notional, 2),
            )

        return RiskDecision(
            allowed=True,
            reserved_risk=round(projected_risk, 2),
            projected_notional=round(projected_notional, 2),
        )

    def reserve(self, sizing):
        self.reserved_risk += sizing.risk_amount
        self.reserved_notional += sizing.notional

    def release(self, risk_amount: float = 0.0, notional: float = 0.0):
        self.reserved_risk = max(0.0, self.reserved_risk - risk_amount)
        self.reserved_notional = max(0.0, self.reserved_notional - notional)

    def apply_closed_pnl(self, pnl: float):
        self.realized_pnl += pnl
        self.current_capital = self.starting_capital + self.realized_pnl
        if self.realized_pnl <= -(self.starting_capital * self.max_daily_loss_pct):
            self.risk_halt = True
            self.risk_halt_reason = "max_daily_loss_reached"

    def state(self) -> dict:
        return {
            "starting_capital": self.starting_capital,
            "current_capital": round(self.current_capital, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "reserved_risk": round(self.reserved_risk, 2),
            "reserved_notional": round(self.reserved_notional, 2),
            "max_open_positions": self.max_open_positions,
            "max_positions_per_symbol": self.max_positions_per_symbol,
            "max_total_risk_pct": self.max_total_risk_pct,
            "max_total_notional_pct": self.max_total_notional_pct,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "risk_halt": self.risk_halt,
            "risk_halt_reason": self.risk_halt_reason,
        }

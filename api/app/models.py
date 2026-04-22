from dataclasses import dataclass

@dataclass
class TradeOutcome:
    pnl: float
    planned_risk: float
    holding_minutes: float
    entry_slippage: float = 0.0
    exit_slippage: float = 0.0
    stop_loss_hit: bool = False

@dataclass
class MarketRegime:
    regime_id: str

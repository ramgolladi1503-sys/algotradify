from pydantic import BaseModel, Field


class TradeOutcome(BaseModel):
    pnl: float
    risk: float = Field(default=1.0, gt=0)
    hold: float = Field(default=1.0, ge=0)
    adx: float = Field(default=30.0, ge=0)
    compression: float = Field(default=0.2, ge=0, le=1)


class MarketRegime(BaseModel):
    regime: str

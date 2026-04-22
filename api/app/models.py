from typing import List
from pydantic import BaseModel, Field


class TradeOutcome(BaseModel):
    pnl: float
    risk: float = Field(default=1.0, gt=0)
    hold: float = Field(default=1.0, ge=0)
    adx: float = Field(default=30.0, ge=0)
    compression: float = Field(default=0.2, ge=0, le=1)


class MarketRegime(BaseModel):
    regime: str


class OpportunityCandidate(BaseModel):
    candidate_id: str
    symbol: str
    side: str
    strategy: str
    arm_id: str
    regime: str
    confidence: float = Field(ge=0, le=1)
    momentum: float = Field(ge=0, le=1)
    liquidity: float = Field(ge=0, le=1)
    volatility: float = Field(ge=0, le=1)
    fallback_used: bool = False
    executable: bool = True
    score: float = Field(default=0, ge=0, le=1)
    rank: int = 0
    rationale: List[str] = []

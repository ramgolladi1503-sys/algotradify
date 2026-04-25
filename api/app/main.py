from fastapi import FastAPI
from .service import BanditService
from .models import TradeOutcome
from .market_data import MarketTick

app = FastAPI()
service = BanditService()

@app.get("/runtime/health")
def health():
    return {"status": "ok"}

@app.get("/opportunities")
def opportunities(adx: float = 30, compression: float = 0.2):
    service.update_regime(adx, compression)
    return service.build_opportunities()

@app.post("/market/tick")
def ingest_tick(tick: MarketTick):
    return service.ingest_market(tick)

@app.get("/market/snapshot")
def snapshots():
    return service.get_market()

@app.get("/market/quality")
def quality():
    return service.get_market_quality()

@app.get("/market/stale")
def stale():
    return service.get_stale()

@app.get("/paper/bandit/arms")
def arms():
    return service.get_arms()

@app.get("/paper/regime/current")
def regime():
    return service.get_regime()

@app.post("/paper/trade")
def trade(data: TradeOutcome):
    return {"reward": service.record_trade(data)}

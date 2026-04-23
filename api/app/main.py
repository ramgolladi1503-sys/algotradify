from fastapi import FastAPI
from .service import BanditService
from .models import TradeOutcome

app = FastAPI()
service = BanditService()

@app.get("/runtime/health")
def health():
    return {"status": "ok"}

@app.get("/opportunities")
def opportunities(adx: float = 30, compression: float = 0.2):
    service.update_regime(adx, compression)
    return service.build_opportunities()

@app.get("/paper/bandit/arms")
def arms():
    return service.get_arms()

@app.get("/paper/regime/current")
def regime():
    return service.get_regime()

@app.post("/paper/trade")
def trade(data: TradeOutcome):
    return {"reward": service.record_trade(data)}

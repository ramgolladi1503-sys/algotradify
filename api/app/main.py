from fastapi import FastAPI
from .service import BanditService
from .models import TradeOutcome

app = FastAPI()
service = BanditService()

@app.get("/runtime/health")
def health():
    return {"status": "ok"}

@app.get("/opportunities")
def opportunities():
    arm = service.select_arm()
    return [{"arm": arm.arm_id, "score": arm.avg}]

@app.get("/paper/bandit/arms")
def arms():
    return service.get_arms()

@app.get("/paper/regime/current")
def regime():
    return service.get_regime()

@app.post("/paper/trade")
def trade(data: TradeOutcome):
    return {"reward": service.record_trade(data)}

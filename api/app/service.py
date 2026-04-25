from .bandit import Arm
from .reward import compute_reward
from .regime import detect_regime
from .models import OpportunityCandidate
from .market_data import MarketDataStore
from .execution_gate import ExecutionGate
import uuid

class BanditService:
    def __init__(self):
        self.arms = {
            "trend": Arm("trend", ["trending"]),
            "mean": Arm("mean", ["sideways"]),
        }
        self.regime = "trending"
        self.market = MarketDataStore()
        self.gate = ExecutionGate()

    def update_regime(self, adx, compression):
        self.regime = detect_regime(adx, compression)

    def select_arm(self):
        eligible = [a for a in self.arms.values() if self.regime in a.regimes and a.active]
        if not eligible:
            return list(self.arms.values())[0]
        return max(eligible, key=lambda a: a.avg)

    def build_opportunities(self):
        selected_arm = self.select_arm()
        snapshots = self.market.all_snapshots()
        candidates = []

        for snap in snapshots:
            c = OpportunityCandidate(
                candidate_id=str(uuid.uuid4()),
                symbol=snap.symbol,
                side="BUY" if self.regime == "trending" else "SELL",
                strategy="market_driven",
                arm_id=selected_arm.arm_id,
                regime=self.regime,
                confidence=0.6,
                momentum=0.6,
                liquidity=snap.liquidity_score,
                volatility=0.6,
                fallback_used=snap.data_quality == "fallback",
                executable=False,
                rationale=[f"data_quality={snap.data_quality}"]
            )

            score = (
                0.3 * c.confidence +
                0.25 * c.momentum +
                0.25 * c.liquidity +
                0.2 * c.volatility
            )

            c.score = max(min(score,1),0)

            decision = self.gate.evaluate(c, snap)

            c.executable = decision.execution_allowed
            c.rationale.extend(decision.blockers or [])
            c.rationale.extend(decision.warnings or [])
            c.rationale.append(f"status={decision.status}")

            candidates.append(c)

        candidates.sort(key=lambda x: x.score, reverse=True)

        for i, c in enumerate(candidates, start=1):
            c.rank = i

        return candidates

    def ingest_market(self, tick):
        return self.market.ingest_tick(tick)

    def get_market(self):
        return self.market.all_snapshots()

    def get_market_quality(self):
        return self.market.quality_summary()

    def get_stale(self):
        return self.market.stale_snapshots()

    def record_trade(self, data):
        self.update_regime(data.adx, data.compression)
        arm = self.select_arm()
        reward = compute_reward(data.pnl, data.risk, data.hold)
        arm.update(reward)
        return reward

    def get_arms(self):
        return {
            k:{
                "avg":v.avg,
                "pulls":v.pulls,
                "active":v.active,
                "disabled_reason":v.disabled_reason
            }
            for k,v in self.arms.items()
        }

    def get_regime(self):
        return {"regime": self.regime}

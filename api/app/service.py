from .bandit import Arm
from .reward import compute_reward
from .regime import detect_regime
from .models import OpportunityCandidate
import uuid

class BanditService:
    def __init__(self):
        self.arms = {
            "trend": Arm("trend", ["trending"]),
            "mean": Arm("mean", ["sideways"]),
        }
        self.regime = "trending"

    def update_regime(self, adx, compression):
        self.regime = detect_regime(adx, compression)

    def select_arm(self):
        eligible = [a for a in self.arms.values() if self.regime in a.regimes and a.active]
        if not eligible:
            return list(self.arms.values())[0]
        return max(eligible, key=lambda a: a.avg)

    def _seed_candidates(self):
        # minimal synthetic candidates per regime
        base = []
        if self.regime == "trending":
            base = [
                {"symbol":"NIFTY","side":"BUY","strategy":"breakout","confidence":0.7,"momentum":0.8,"liquidity":0.7,"volatility":0.6},
                {"symbol":"BANKNIFTY","side":"BUY","strategy":"pullback","confidence":0.6,"momentum":0.65,"liquidity":0.6,"volatility":0.5},
            ]
        elif self.regime == "sideways":
            base = [
                {"symbol":"NIFTY","side":"SELL","strategy":"mean_reversion","confidence":0.65,"momentum":0.3,"liquidity":0.7,"volatility":0.4},
                {"symbol":"BANKNIFTY","side":"BUY","strategy":"range_low","confidence":0.6,"momentum":0.35,"liquidity":0.65,"volatility":0.4},
            ]
        else:
            base = [
                {"symbol":"NIFTY","side":"BUY","strategy":"vol_spike","confidence":0.55,"momentum":0.6,"liquidity":0.6,"volatility":0.8},
            ]

        return base

    def _score(self, c, selected_arm):
        score = (
            0.3 * c.confidence +
            0.25 * c.momentum +
            0.2 * c.liquidity +
            0.25 * c.volatility
        )

        if c.fallback_used:
            score -= 0.3

        if not c.executable:
            score -= 0.2

        if c.arm_id == selected_arm.arm_id:
            score += 0.05

        return max(min(score,1),0)

    def build_opportunities(self):
        selected_arm = self.select_arm()
        raw = self._seed_candidates()

        candidates = []
        for r in raw:
            c = OpportunityCandidate(
                candidate_id=str(uuid.uuid4()),
                symbol=r["symbol"],
                side=r["side"],
                strategy=r["strategy"],
                arm_id=selected_arm.arm_id,
                regime=self.regime,
                confidence=r["confidence"],
                momentum=r["momentum"],
                liquidity=r["liquidity"],
                volatility=r["volatility"],
                fallback_used=False,
                executable=True,
                rationale=["synthetic candidate","regime matched"]
            )
            c.score = self._score(c, selected_arm)
            candidates.append(c)

        candidates.sort(key=lambda x: x.score, reverse=True)

        for i, c in enumerate(candidates, start=1):
            c.rank = i

        return candidates

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

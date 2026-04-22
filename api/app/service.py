from .bandit import Arm
from .reward import compute_reward
from .regime import detect_regime

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

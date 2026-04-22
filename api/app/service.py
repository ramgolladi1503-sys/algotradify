from .bandit import Arm
from .reward import compute_reward

class BanditService:
    def __init__(self):
        self.arms = {
            "trend": Arm("trend", ["trending"]),
            "mean": Arm("mean", ["sideways"]),
        }
        self.regime = "trending"

    def select_arm(self):
        eligible = [a for a in self.arms.values() if self.regime in a.regimes and a.active]
        if not eligible:
            return list(self.arms.values())[0]
        return max(eligible, key=lambda a: a.avg)

    def record_trade(self, data):
        arm = self.select_arm()
        reward = compute_reward(data.get("pnl",0), data.get("risk",1), data.get("hold",1))
        arm.update(reward)
        return reward

    def get_arms(self):
        return {k:{"avg":v.avg,"pulls":v.pulls} for k,v in self.arms.items()}

    def get_regime(self):
        return {"regime": self.regime}

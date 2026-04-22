class Arm:
    def __init__(self, arm_id, regimes):
        self.arm_id = arm_id
        self.regimes = set(regimes)
        self.pulls = 0
        self.total = 0.0
        self.active = True
        self.disabled_reason = None

    @property
    def avg(self):
        return self.total / self.pulls if self.pulls else 0.0

    def update(self, reward):
        self.pulls += 1
        self.total += reward
        self._maybe_disable()

    def _maybe_disable(self):
        if self.pulls >= 15 and self.avg < -0.3:
            self.active = False
            self.disabled_reason = "poor_performance"

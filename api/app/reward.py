def compute_reward(pnl, risk, hold_minutes):
    risk = max(risk, 1.0)
    r = pnl / risk
    hold_penalty = min(hold_minutes / 240.0, 0.75)
    return max(min(r - hold_penalty, 2.0), -2.0)

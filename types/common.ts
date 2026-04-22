export type BotMode = "AUTO" | "MANUAL" | "PAPER" | "DISABLED" | (string & {});
export type HealthStatus = "LIVE" | "DEGRADED" | "BLOCKED" | "MARKET_CLOSED" | "NO_FEED" | (string & {});
export type ExecutionStatus = "READY" | "WATCH" | "BLOCKED" | "EXECUTED" | "REJECTED" | "CANCELLED" | (string & {});
export type Severity = "info" | "warning" | "error" | "critical" | (string & {});
export type SymbolName = "NIFTY" | "BANKNIFTY" | "SENSEX" | (string & {});
export type StrategyName = "momentum_breakout" | "mean_reversion" | "pullback" | "zero_hero" | "ensemble" | (string & {});
export type BlockerCode =
  | "STALE_OPTION_LTP"
  | "NO_LIVE_OPTION_FEED"
  | "NO_TOKEN"
  | "ENTRY_PRICE_MISSING"
  | "HIGH_SPREAD"
  | "RISK_HALT"
  | "READINESS_FAILED"
  | "QUOTE_MISMATCH"
  | (string & {});

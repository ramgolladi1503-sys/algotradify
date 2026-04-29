import { BotMode, HealthStatus } from "./common";

export interface RuntimeHealth {
  botMode: BotMode;
  healthStatus: HealthStatus;
  marketOpen: boolean;
  wsConnected: boolean;
  feedConnected: boolean;
  runtimeState: string;
  quoteAgeSec: number | null;
  depthAgeSec: number | null;
  subscribedTokensCount: number | null;
  subscribedOptionTokensCount: number | null;
  missingOptionTokensCount: number | null;
  updatedAt: string;
}

export interface RiskState {
  currentExposurePct: number;
  maxExposurePct: number;
  dayPnl: number;
  maxDailyLossLimit: number;
  riskHalt: boolean;
  riskHaltReason?: string | null;
}

export interface ExecutionState {
  readyCount: number;
  blockedCount: number;
  watchCount: number;
  executedCount: number;
  autoExecutionEnabled: boolean;
}

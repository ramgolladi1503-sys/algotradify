import { BlockerCode, ExecutionStatus, StrategyName, SymbolName } from "./common";

export interface DecisionTraceStep {
  key: string;
  label: string;
  status: "done" | "failed" | "skipped" | "active";
  timestamp: string;
  reason?: string | null;
}

export interface RiskCheck {
  name: string;
  passed: boolean;
  value?: string | number | null;
  threshold?: string | number | null;
  reason?: string | null;
}

export interface TradeDetail {
  tradeId: string;
  symbol: SymbolName;
  strategy: StrategyName;
  status: ExecutionStatus;
  instrumentType: "CE" | "PE" | "FUT" | "SPOT";
  strike?: number | null;
  expiry?: string | null;
  tradingsymbol?: string | null;
  confidenceRaw: number;
  confidenceFinal: number;
  entry: number | null;
  stoploss: number | null;
  target: number | null;
  blockers: BlockerCode[];
  warnings: string[];
  riskChecks: RiskCheck[];
  decisionTrace: DecisionTraceStep[];
  permissionReason?: string | null;
  finalAction?: string | null;
  executionEntryStatus?: string | null;
  executionStatusReason?: string | null;
  quoteAgeSec?: number | null;
  spreadPct?: number | null;
  liquidityScore?: number | null;
  momentumScore?: number | null;
  regimeFitScore?: number | null;
  createdAt: string;
  updatedAt: string;
}

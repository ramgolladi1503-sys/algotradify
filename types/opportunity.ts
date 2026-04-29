import { BlockerCode, ExecutionStatus, StrategyName, SymbolName } from "./common";

export interface OpportunityScoreBreakdown {
  momentumScore: number;
  liquidityScore: number;
  spreadScore: number;
  regimeFitScore: number;
  confidenceRaw: number;
  confidenceFinal: number;
  penaltyTotal: number;
}

export interface Opportunity {
  id: string;
  symbol: SymbolName;
  strategy: StrategyName;
  status: ExecutionStatus;
  rank: number;
  instrumentType: "CE" | "PE" | "FUT" | "SPOT";
  strike?: number | null;
  expiry?: string | null;
  entry: number | null;
  stoploss: number | null;
  target: number | null;
  rrRatio: number | null;
  spreadQuality: "GOOD" | "MID" | "WIDE" | "UNKNOWN";
  liquidityQuality: "GOOD" | "MID" | "LOW" | "UNKNOWN";
  blockers: BlockerCode[];
  warnings: { code: string; message: string }[];
  score: OpportunityScoreBreakdown;
  executionAllowed: boolean;
  permissionReason?: string | null;
  finalAction?: string | null;
  createdAt: string;
  updatedAt: string;
}

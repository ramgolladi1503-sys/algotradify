import type { Opportunity } from "@/types/opportunity";
import type { Incident } from "@/types/incident";
import type { ExecutionState, RiskState, RuntimeHealth } from "@/types/runtime";
import type { BlockerCode, ExecutionStatus } from "@/types/common";

export type LiveEvent = {
  type: string;
  receivedAt: string;
  payload: unknown;
  raw: unknown;
};

function nowIso(): string {
  return new Date().toISOString();
}

export function normalizeLiveEvent(raw: unknown): LiveEvent {
  const receivedAt = nowIso();
  if (raw && typeof raw === "object") {
    const obj = raw as { type?: unknown; payload?: unknown };
    const type = typeof obj.type === "string" ? obj.type : "unknown";
    return { type, receivedAt, payload: obj.payload ?? null, raw };
  }
  return { type: "unknown", receivedAt, payload: raw, raw };
}

function _asBlockers(value: unknown): BlockerCode[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v) => typeof v === "string") as BlockerCode[];
}

function _statusFromCandidate(p: any): ExecutionStatus {
  const finalAction = String(p?.final_action || "").toUpperCase();
  const permission = String(p?.permission || "").toUpperCase();
  const exec = String(p?.execution_status || "").toUpperCase();
  if (finalAction === "EXECUTED" || exec === "EXECUTED") return "EXECUTED";
  if (finalAction === "REJECTED" || exec === "REJECTED") return "REJECTED";
  if (permission === "ADVISORY_ONLY" || finalAction === "ADVISORY_ONLY") return "WATCH";
  return "READY";
}

export function toOpportunity(payload: unknown, index: number): Opportunity {
  const p: any = payload || {};
  const now = nowIso();
  const id = String(p.candidate_id || p.trade_id || p.advisory_id || p.trade_key || index);
  const symbol = String(p.symbol || p.underlying || p.index_symbol || "UNKNOWN");
  const strategy = String(p.strategy || p.strategy_family || "unknown_strategy");
  const instrumentTypeRaw = String(p.option_type || p.type || p.instrument_type || "CE").toUpperCase();
  const instrumentType =
    instrumentTypeRaw === "PE" ? "PE" : instrumentTypeRaw === "FUT" ? "FUT" : instrumentTypeRaw === "SPOT" ? "SPOT" : "CE";
  const scoreBreakdown = p.score_breakdown?.components || {};
  const confidenceRaw = Number(scoreBreakdown.confidence_raw ?? p.confidence ?? 0) || 0;
  const confidenceFinal = Number(scoreBreakdown.confidence_final ?? p.confidence ?? 0) || 0;

  return {
    id,
    symbol,
    strategy,
    status: _statusFromCandidate(p),
    rank: Number(p.rank ?? p.rank_score ?? index) || index,
    instrumentType,
    strike: p.strike ?? null,
    expiry: p.expiry ?? p.expiry_date ?? null,
    entry: p.entry_price ?? p.entry ?? null,
    stoploss: p.stop_loss ?? p.stoploss ?? p.stop ?? null,
    target: p.target_price ?? p.target ?? null,
    rrRatio: p.rr_ratio ?? p.rrRatio ?? null,
    spreadQuality: "UNKNOWN",
    liquidityQuality: "UNKNOWN",
    blockers: _asBlockers(p.blockers || p.reasons || p.missing_reasons),
    warnings: [],
    score: {
      momentumScore: Number(scoreBreakdown.setup_strength ?? 0) || 0,
      liquidityScore: Number(scoreBreakdown.liquidity_score ?? 0) || 0,
      spreadScore: Number(scoreBreakdown.spread_score ?? 0) || 0,
      regimeFitScore: Number(scoreBreakdown.regime_fit ?? 0) || 0,
      confidenceRaw,
      confidenceFinal,
      penaltyTotal: Number(scoreBreakdown.penalty_score ?? 0) || 0,
    },
    executionAllowed: String(p.permission || "").toUpperCase() === "EXECUTE",
    permissionReason: p.primary_blocker ?? p.reason ?? null,
    finalAction: p.final_action ?? null,
    createdAt: String(p.created_at || p.createdAt || now),
    updatedAt: String(p.updated_at || p.updatedAt || now),
  };
}

export function toIncident(payload: unknown, index: number): Incident {
  const p: any = payload || {};
  return {
    id: String(p.incident_id || p.id || index),
    severity: String(p.severity || p.sev || "info"),
    code: String(p.code || "UNKNOWN"),
    message: String(p.message || p.reason || ""),
    createdAt: String(p.created_at || p.createdAt || nowIso()),
    raw: p,
  } as any;
}

export function toRuntimeHealth(payload: unknown): RuntimeHealth | null {
  return (payload as any) ?? null;
}

export function toRiskState(payload: unknown): RiskState | null {
  return (payload as any) ?? null;
}

export function toExecutionState(payload: unknown): ExecutionState | null {
  return (payload as any) ?? null;
}

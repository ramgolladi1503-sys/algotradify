import { BlockerCode, Severity, SymbolName } from "./common";

export interface Incident {
  id: string;
  code: BlockerCode;
  severity: Severity;
  symbol?: SymbolName | null;
  stage: string;
  message: string;
  details?: string | null;
  quoteAgeSec?: number | null;
  thresholdSec?: number | null;
  tokenCount?: number | null;
  missingCount?: number | null;
  timestamp: string;
}

export interface VerificationCheck {
  id: string;
  label: string;
  command: string;
  status: "passed" | "failed" | "running" | "unknown";
  lastRunAt?: string | null;
  outputSnippet?: string | null;
}

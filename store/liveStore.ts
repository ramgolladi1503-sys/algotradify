"use client";

import { create } from "zustand";
import { normalizeLiveEvent, toExecutionState, toIncident, toOpportunity, toRuntimeHealth, toRiskState, type LiveEvent } from "@/lib/events/normalize";
import type { Incident } from "@/types/incident";
import type { Opportunity } from "@/types/opportunity";
import type { ExecutionState, RiskState, RuntimeHealth } from "@/types/runtime";

interface LiveStoreState {
  connected: boolean;
  lastHeartbeatAt: string | null;
  runtimeHealth: RuntimeHealth | null;
  riskState: RiskState | null;
  executionState: ExecutionState | null;
  opportunities: Opportunity[];
  incidents: Incident[];
  events: LiveEvent[];
  setConnected: (connected: boolean) => void;
  addRawEvent: (raw: unknown) => void;
}

export const useLiveStore = create<LiveStoreState>((set) => ({
  connected: false,
  lastHeartbeatAt: null,
  runtimeHealth: null,
  riskState: null,
  executionState: null,
  opportunities: [],
  incidents: [],
  events: [],
  setConnected: (connected) => set({ connected }),
  addRawEvent: (raw) =>
    set((state) => {
      const event = normalizeLiveEvent(raw);
      const nextEvents = [event, ...state.events].slice(0, 200);

      if (event.type === "heartbeat") {
        return { ...state, connected: true, lastHeartbeatAt: event.receivedAt, events: nextEvents };
      }

      if (event.type === "candidate_created" || event.type === "trade_executed") {
        const mapped = toOpportunity(event.payload, state.opportunities.length);
        const nextOpportunities = [mapped, ...state.opportunities.filter((item) => item.id !== mapped.id)].slice(0, 100);
        return { ...state, opportunities: nextOpportunities, events: nextEvents };
      }

      if (event.type === "gate_rejected") {
        const mapped = toIncident(event.payload, state.incidents.length);
        return { ...state, incidents: [mapped, ...state.incidents].slice(0, 100), events: nextEvents };
      }

      if (event.type === "runtime_health") {
        return { ...state, runtimeHealth: toRuntimeHealth(event.payload), events: nextEvents };
      }

      if (event.type === "risk_state") {
        return { ...state, riskState: toRiskState(event.payload), events: nextEvents };
      }

      if (event.type === "execution_state") {
        return { ...state, executionState: toExecutionState(event.payload), events: nextEvents };
      }

      return { ...state, events: nextEvents };
    }),
}));

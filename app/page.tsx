"use client";

import { useEffect, useMemo, useState } from "react";
import { useLiveStore } from "@/store/liveStore";

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
}

function wsUrl(api: string): string {
  const configured = process.env.NEXT_PUBLIC_WS_URL;
  if (configured) return configured;
  return api.replace(/^http/i, "ws") + "/ws";
}

export default function HomePage() {
  const api = useMemo(() => apiBase(), []);
  const ws = useMemo(() => wsUrl(api), [api]);
  const live = useLiveStore();
  const [snapshot, setSnapshot] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [opps, setOpps] = useState<any[]>([]);
  const [error, setError] = useState<string>("");

  async function refresh() {
    try {
      const [healthRes, snapRes, oppRes] = await Promise.all([
        fetch(`${api}/runtime/health`),
        fetch(`${api}/runtime/snapshot`),
        fetch(`${api}/opportunities?limit=20`),
      ]);
      if (!healthRes.ok || !snapRes.ok || !oppRes.ok) {
        throw new Error(`fetch_failed health=${healthRes.status} snapshot=${snapRes.status} opp=${oppRes.status}`);
      }
      setHealth(await healthRes.json());
      setSnapshot(await snapRes.json());
      const rows = await oppRes.json();
      setOpps(Array.isArray(rows) ? rows : []);
      setError("");
    } catch (e: any) {
      setError(e?.message || "runtime_fetch_failed");
    }
  }

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const sock = new WebSocket(ws);
    sock.onopen = () => live.setConnected(true);
    sock.onclose = () => live.setConnected(false);
    sock.onmessage = (evt) => {
      try {
        const parsed = JSON.parse(evt.data);
        live.addRawEvent(parsed);
        if (parsed?.type === "runtime_snapshot") {
          setSnapshot(parsed.payload);
        }
      } catch {
        live.addRawEvent({ type: "raw_ws", payload: String(evt.data) });
      }
    };
    return () => sock.close();
  }, [ws]);

  return (
    <div className="mx-auto max-w-6xl p-6">
      <h1 className="text-2xl font-semibold">AlgoTradify</h1>
      <p className="text-sm text-slate-300">Runtime bridge UI (offline-capable via `core_bot/.runtime` artifacts).</p>

      {error ? <div className="mt-4 rounded bg-red-950/40 p-3 text-red-200">{error}</div> : null}

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded bg-slate-900/60 p-4">
          <div className="font-medium">Runtime Health</div>
          <div className="mt-2 text-sm text-slate-200">status: {health?.status || "unknown"}</div>
          <div className="text-sm text-slate-200">mode: {health?.mode || "-"}</div>
          <div className="text-sm text-slate-200">market_open: {String(health?.market_open)}</div>
        </div>

        <div className="rounded bg-slate-900/60 p-4">
          <div className="font-medium">Cycle Snapshot</div>
          <div className="mt-2 text-sm text-slate-200">cycle_stage: {snapshot?.cycle_stage || "-"}</div>
          <div className="text-sm text-slate-200">cycle_ok: {String(snapshot?.cycle_ok)}</div>
          <div className="text-sm text-slate-200">top_executable: {snapshot?.top_executable_count ?? 0}</div>
          <div className="text-sm text-slate-200">top_advisory: {snapshot?.top_advisory_count ?? 0}</div>
        </div>
      </div>

      <div className="mt-6 rounded bg-slate-900/60 p-4">
        <div className="font-medium">Opportunities</div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-slate-300">
              <tr>
                <th className="py-2 pr-3">symbol</th>
                <th className="py-2 pr-3">strategy</th>
                <th className="py-2 pr-3">bucket</th>
                <th className="py-2 pr-3">permission</th>
                <th className="py-2 pr-3">final_action</th>
                <th className="py-2 pr-3">score</th>
              </tr>
            </thead>
            <tbody className="text-slate-100">
              {opps.map((o, idx) => (
                <tr key={o.candidate_id || idx} className="border-t border-slate-700/60">
                  <td className="py-2 pr-3">{o.symbol || "-"}</td>
                  <td className="py-2 pr-3">{o.strategy || "-"}</td>
                  <td className="py-2 pr-3">{o.bucket || "-"}</td>
                  <td className="py-2 pr-3">{o.permission || "-"}</td>
                  <td className="py-2 pr-3">{o.final_action || "-"}</td>
                  <td className="py-2 pr-3">{o.score ?? "-"}</td>
                </tr>
              ))}
              {!opps.length ? (
                <tr>
                  <td className="py-2 pr-3 text-slate-300" colSpan={6}>
                    no opportunities yet
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6 rounded bg-slate-900/60 p-4">
        <div className="font-medium">Live Events</div>
        <div className="mt-3 space-y-2 text-xs text-slate-200">
          {live.events.slice(0, 30).map((e, i) => (
            <div key={i} className="rounded border border-slate-700/60 p-2">
              <div className="font-semibold">{e.type}</div>
              <div className="break-words opacity-90">{JSON.stringify(e.payload)}</div>
            </div>
          ))}
          {!live.events.length ? <div className="text-slate-300">no events yet</div> : null}
        </div>
      </div>
    </div>
  );
}


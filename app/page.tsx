"use client";

import { useEffect, useState } from "react";

const API = "http://localhost:8000";

export default function Dashboard() {
  const [health, setHealth] = useState<any>(null);
  const [opps, setOpps] = useState<any[]>([]);
  const [paperPositions, setPaperPositions] = useState<any[]>([]);
  const [paperPnl, setPaperPnl] = useState<any>({});

  const refresh = async () => {
    const [healthRes, oppsRes, positionsRes, pnlRes] = await Promise.all([
      fetch(`${API}/runtime/health`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/opportunities`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/paper/positions`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/paper/pnl`).then((r) => r.json()).catch(() => null),
    ]);

    if (healthRes?.payload) setHealth(healthRes.payload);
    if (oppsRes?.payload?.items) setOpps(oppsRes.payload.items);
    if (positionsRes?.payload?.items) setPaperPositions(positionsRes.payload.items);
    if (pnlRes?.payload) setPaperPnl(pnlRes.payload);
  };

  const trigger = async (action: string, o: any) => {
    await fetch(`${API}/actions/${action.toLowerCase()}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        trade_id: o.trade_id,
        trade_key: o.trade_key,
        symbol: o.symbol,
      }),
    }).catch(() => null);
    await refresh();
  };

  useEffect(() => {
    refresh();

    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onmessage = (e) => {
      const d = JSON.parse(e.data);
      if (d.payload?.opportunities?.items) setOpps(d.payload.opportunities.items);
      if (d.payload?.runtime_health) setHealth(d.payload.runtime_health);
      if (d.payload?.paper_positions?.items) setPaperPositions(d.payload.paper_positions.items);
      if (d.payload?.paper_pnl) setPaperPnl(d.payload.paper_pnl);
    };

    return () => ws.close();
  }, []);

  return (
    <div style={{ padding: 20 }}>
      <h1>AlgoTradify</h1>

      <div className="card" style={{ marginBottom: 20 }}>
        <h3>Runtime</h3>
        <div>Market: {String(health?.market_open)}</div>
        <div>Mode: {health?.mode}</div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <h3>Paper PnL</h3>
        <div>Open: {paperPnl?.open_count ?? 0}</div>
        <div>Closed: {paperPnl?.closed_count ?? 0}</div>
        <div>Realized: {paperPnl?.realized_pnl ?? 0}</div>
        <div>Unrealized: {paperPnl?.unrealized_pnl ?? 0}</div>
        <div>Net: {paperPnl?.net_pnl ?? 0}</div>
        <div>Win Rate: {paperPnl?.win_rate ?? "—"}</div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <h3>Paper Positions ({paperPositions.length})</h3>
        {paperPositions.length === 0 ? <div>No paper positions yet.</div> : null}
        {paperPositions.map((p, i) => (
          <div key={p.paper_position_id || i} style={{ borderBottom: "1px solid #222", padding: 10 }}>
            <div><b>{p.symbol || "N/A"}</b> | {p.status || "—"}</div>
            <div>Entry: {p.entry_price ?? "—"} | Current: {p.current_price ?? "—"}</div>
            <div>Target: {p.target_price ?? "—"} | Stop: {p.stop_price ?? "—"}</div>
            <div>Unrealized: {p.unrealized_pnl ?? 0} | Realized: {p.realized_pnl ?? 0}</div>
            <div>Exit Reason: {p.exit_reason || "OPEN"}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Opportunities ({opps.length})</h3>
        {opps.map((o, i) => (
          <div key={i} style={{ borderBottom: "1px solid #222", padding: 10 }}>
            <div><b>{o.symbol || "N/A"}</b> | Score: {o.score ?? "—"} | {o.decision || "—"}</div>
            <div style={{ marginTop: 6, display: "flex", gap: 6 }}>
              <button onClick={() => trigger("ENTER", o)}>ENTER</button>
              <button onClick={() => trigger("SKIP", o)}>SKIP</button>
              <button onClick={() => trigger("FORCE", o)}>FORCE</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

const API = "http://localhost:8000";

export default function Dashboard() {
  const [health, setHealth] = useState<any>(null);
  const [opps, setOpps] = useState<any[]>([]);

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
    });
  };

  useEffect(() => {
    fetch(`${API}/runtime/health`)
      .then((r) => r.json())
      .then((d) => setHealth(d.payload));

    fetch(`${API}/opportunities`)
      .then((r) => r.json())
      .then((d) => setOpps(d.payload.items || []));

    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onmessage = (e) => {
      const d = JSON.parse(e.data);
      if (d.payload?.opportunities?.items) {
        setOpps(d.payload.opportunities.items);
      }
      if (d.payload?.runtime_health) {
        setHealth(d.payload.runtime_health);
      }
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

      <div className="card">
        <h3>Opportunities ({opps.length})</h3>
        {opps.map((o, i) => (
          <div key={i} style={{ borderBottom: "1px solid #222", padding: 10 }}>
            <div><b>{o.symbol}</b> | Score: {o.score} | {o.decision}</div>

            <div style={{ marginTop: 6, display: "flex", gap: 6 }}>
              <button onClick={() => trigger("ENTER", o)} style={{ background: "green" }}>ENTER</button>
              <button onClick={() => trigger("SKIP", o)} style={{ background: "orange" }}>SKIP</button>
              <button onClick={() => trigger("FORCE", o)} style={{ background: "red" }}>FORCE</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

export default function Dashboard() {
  const [health, setHealth] = useState<any>(null);
  const [opps, setOpps] = useState<any[]>([]);

  useEffect(() => {
    fetch("http://localhost:8000/runtime/health")
      .then((r) => r.json())
      .then((d) => setHealth(d.payload))
      .catch(() => {});

    fetch("http://localhost:8000/opportunities")
      .then((r) => r.json())
      .then((d) => setOpps(d.payload.items || []))
      .catch(() => {});

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
      <h1>AlgoTradify Dashboard</h1>

      <div className="card" style={{ marginBottom: 20 }}>
        <h3>Runtime Health</h3>
        <pre>{JSON.stringify(health, null, 2)}</pre>
      </div>

      <div className="card">
        <h3>Opportunities ({opps.length})</h3>
        {opps.map((o, i) => (
          <div key={i} style={{ borderBottom: "1px solid #222", padding: 10 }}>
            <div><b>{o.symbol || "N/A"}</b></div>
            <div>Score: {o.score}</div>
            <div>Decision: {o.decision}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

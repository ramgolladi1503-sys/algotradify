import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

const ENV = import.meta.env || {};
const API_BASE =
  ENV.VITE_API_BASE_URL ||
  ENV.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";
const WS_URL =
  ENV.VITE_WS_URL ||
  ENV.NEXT_PUBLIC_WS_URL ||
  API_BASE.replace(/^http/i, "ws") + "/ws";

function App() {
  const [events, setEvents] = useState([]);
  const [health, setHealth] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [error, setError] = useState("");

  function pushEvent(eventObj) {
    setEvents((prev) => [eventObj, ...prev.slice(0, 80)]);
  }

  async function fetchRuntime() {
    try {
      const [healthRes, snapshotRes, oppRes] = await Promise.all([
        fetch(`${API_BASE}/runtime/health`),
        fetch(`${API_BASE}/runtime/snapshot`),
        fetch(`${API_BASE}/opportunities?limit=20`),
      ]);

      if (!healthRes.ok || !snapshotRes.ok || !oppRes.ok) {
        throw new Error(
          `backend fetch failed: health=${healthRes.status} snapshot=${snapshotRes.status} opp=${oppRes.status}`
        );
      }

      const [healthJson, snapshotJson, oppJson] = await Promise.all([
        healthRes.json(),
        snapshotRes.json(),
        oppRes.json(),
      ]);

      setHealth(healthJson);
      setSnapshot(snapshotJson);
      setOpportunities(Array.isArray(oppJson) ? oppJson : []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown runtime fetch error");
    }
  }

  function connect() {
    const ws = new WebSocket(WS_URL);

    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        pushEvent(d);
        if (d?.type === "runtime_snapshot" && d?.payload) {
          setSnapshot(d.payload);
        }
      } catch {
        pushEvent({ type: "raw_ws", payload: e.data });
      }
    };

    ws.onclose = () => setTimeout(connect, 1000);
    ws.onerror = () => setTimeout(connect, 1000);
  }

  useEffect(() => {
    connect();
    fetchRuntime();
    const timer = setInterval(fetchRuntime, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{ background: "#0b1220", color: "#e8eefc", minHeight: "100vh", padding: 20 }}>
      <h2 style={{ marginTop: 0 }}>Tradebot Live Runtime</h2>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
        <div style={{ background: "#121c34", padding: 12, borderRadius: 8, minWidth: 250 }}>
          <div style={{ fontWeight: 700 }}>Runtime Health</div>
          <div>status: {health?.status || "unknown"}</div>
          <div>mode: {health?.mode || "-"}</div>
          <div>market_open: {String(health?.market_open)}</div>
          <div>feed_blocked: {String(health?.feed?.blocked)}</div>
        </div>
        <div style={{ background: "#121c34", padding: 12, borderRadius: 8, minWidth: 250 }}>
          <div style={{ fontWeight: 700 }}>Cycle Snapshot</div>
          <div>cycle_stage: {snapshot?.cycle_stage || "-"}</div>
          <div>cycle_ok: {String(snapshot?.cycle_ok)}</div>
          <div>top_executable: {snapshot?.top_executable_count ?? 0}</div>
          <div>top_advisory: {snapshot?.top_advisory_count ?? 0}</div>
        </div>
      </div>

      {error ? (
        <div style={{ color: "#fecaca", background: "#3f1d1d", padding: 10, borderRadius: 8, marginBottom: 16 }}>
          {error}
        </div>
      ) : null}

      <h3 style={{ marginBottom: 8 }}>Opportunities</h3>
      <div style={{ overflowX: "auto", marginBottom: 20 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", background: "#121c34" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 8 }}>symbol</th>
              <th style={{ textAlign: "left", padding: 8 }}>strategy</th>
              <th style={{ textAlign: "left", padding: 8 }}>bucket</th>
              <th style={{ textAlign: "left", padding: 8 }}>permission</th>
              <th style={{ textAlign: "left", padding: 8 }}>final_action</th>
              <th style={{ textAlign: "left", padding: 8 }}>score</th>
            </tr>
          </thead>
          <tbody>
            {opportunities.map((o, i) => (
              <tr key={o.candidate_id || i} style={{ borderTop: "1px solid #2f3b5a" }}>
                <td style={{ padding: 8 }}>{o.symbol || "-"}</td>
                <td style={{ padding: 8 }}>{o.strategy || "-"}</td>
                <td style={{ padding: 8 }}>{o.bucket || "-"}</td>
                <td style={{ padding: 8 }}>{o.permission || "-"}</td>
                <td style={{ padding: 8 }}>{o.final_action || "-"}</td>
                <td style={{ padding: 8 }}>{o.score ?? "-"}</td>
              </tr>
            ))}
            {!opportunities.length ? (
              <tr>
                <td style={{ padding: 8 }} colSpan={6}>
                  no opportunities yet
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <h3 style={{ marginBottom: 8 }}>Live Event Feed</h3>
      {events.map((e, i) => (
        <div key={i} style={{ border: "1px solid #334155", padding: 10, marginBottom: 10, borderRadius: 8 }}>
          <div style={{ fontWeight: 700 }}>{e.type}</div>
          <div style={{ opacity: 0.95, wordBreak: "break-word" }}>{JSON.stringify(e.payload)}</div>
        </div>
      ))}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App/>);

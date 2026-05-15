import React, { useEffect, useMemo, useState } from "react";
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

const cardStyle = {
  background: "#121c34",
  border: "1px solid #24314f",
  padding: 14,
  borderRadius: 12,
  boxShadow: "0 10px 30px rgba(0,0,0,0.18)",
};

const muted = { color: "#99a7c7" };

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function text(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function statusColor(value) {
  const upper = String(value || "").toUpperCase();
  if (["OK", "PASS", "READY", "ALLOWED", "QUALIFIED", "SELECTED", "FILLED", "POSITION_CLOSED"].includes(upper)) {
    return { background: "#123c2c", color: "#a7f3d0", borderColor: "#166534" };
  }
  if (upper.includes("BLOCK") || upper.includes("FAIL") || upper.includes("REJECT") || upper.includes("UNKNOWN")) {
    return { background: "#421c24", color: "#fecaca", borderColor: "#7f1d1d" };
  }
  return { background: "#2b2a16", color: "#fde68a", borderColor: "#854d0e" };
}

function StatusPill({ value }) {
  return (
    <span
      style={{
        ...statusColor(value),
        border: "1px solid",
        borderRadius: 999,
        padding: "3px 8px",
        fontSize: 12,
        fontWeight: 700,
        whiteSpace: "nowrap",
      }}
    >
      {text(value)}
    </span>
  );
}

function Card({ title, children, right }) {
  return (
    <section style={cardStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <h3 style={{ margin: 0, fontSize: 16 }}>{title}</h3>
        {right || null}
      </div>
      {children}
    </section>
  );
}

function Metric({ label, value, pill = false }) {
  return (
    <div style={{ minWidth: 120 }}>
      <div style={{ ...muted, fontSize: 12 }}>{label}</div>
      <div style={{ fontWeight: 800, marginTop: 3 }}>{pill ? <StatusPill value={value} /> : text(value)}</div>
    </div>
  );
}

function ListChips({ items, empty = "none" }) {
  const values = safeArray(items);
  if (!values.length) return <span style={muted}>{empty}</span>;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {values.slice(0, 8).map((item, index) => (
        <span key={`${item}-${index}`} style={{ border: "1px solid #334155", borderRadius: 999, padding: "3px 8px", color: "#dbeafe" }}>
          {text(item)}
        </span>
      ))}
      {values.length > 8 ? <span style={muted}>+{values.length - 8} more</span> : null}
    </div>
  );
}

function Table({ columns, rows, empty }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} style={{ textAlign: "left", padding: 8, color: "#bfdbfe", borderBottom: "1px solid #2f3b5a", fontSize: 12 }}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={row.candidate_id || row.id || rowIndex} style={{ borderTop: "1px solid #1f2a44" }}>
              {columns.map((column) => (
                <td key={column.key} style={{ padding: 8, verticalAlign: "top", fontSize: 13 }}>
                  {column.render ? column.render(row) : text(row[column.key])}
                </td>
              ))}
            </tr>
          ))}
          {!rows.length ? (
            <tr>
              <td style={{ padding: 10, color: "#99a7c7" }} colSpan={columns.length}>
                {empty}
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [events, setEvents] = useState([]);
  const [state, setState] = useState({
    health: null,
    preflight: null,
    snapshot: null,
    opportunities: [],
    candidateTruth: [],
    opportunityLayer: null,
    executionReadiness: [],
    tradeQuality: [],
    topExecutable: null,
    fillLifecycle: null,
  });
  const [errors, setErrors] = useState([]);
  const [lastRefresh, setLastRefresh] = useState(null);

  const summary = useMemo(() => {
    const realCandidates = state.candidateTruth.filter((row) => row.truth_status === "REAL").length;
    const executionAllowed = state.executionReadiness.filter((row) => row.execution_allowed).length;
    const blockedReadiness = state.executionReadiness.filter((row) => !row.execution_allowed).length;
    const qualityReady = state.tradeQuality.filter((row) => row.status === "QUALIFIED" || row.status === "DEGRADED_BY_WARNINGS").length;
    return { realCandidates, executionAllowed, blockedReadiness, qualityReady };
  }, [state]);

  function pushEvent(eventObj) {
    setEvents((prev) => [eventObj, ...prev.slice(0, 80)]);
  }

  async function fetchJson(path) {
    const response = await fetch(`${API_BASE}${path}`);
    if (!response.ok) throw new Error(`${path} -> HTTP ${response.status}`);
    return response.json();
  }

  async function fetchControlTower() {
    const requests = [
      ["health", "/runtime/health"],
      ["preflight", "/runtime/preflight"],
      ["snapshot", "/runtime/snapshot"],
      ["opportunities", "/opportunities?limit=20"],
      ["candidateTruth", "/candidate-truth?limit=20"],
      ["opportunityLayer", "/opportunity-layer?limit=20"],
      ["executionReadiness", "/execution-readiness?limit=20"],
      ["tradeQuality", "/trade-quality?limit=20"],
      ["topExecutable", "/top-executable?limit=20"],
      ["fillLifecycle", "/fill-lifecycle"],
    ];

    const results = await Promise.allSettled(requests.map(([_, path]) => fetchJson(path)));
    const next = {};
    const nextErrors = [];

    results.forEach((result, index) => {
      const [key, path] = requests[index];
      if (result.status === "fulfilled") {
        next[key] = result.value;
      } else {
        nextErrors.push(`${path}: ${result.reason?.message || "failed"}`);
      }
    });

    setState((prev) => ({ ...prev, ...next }));
    setErrors(nextErrors);
    setLastRefresh(new Date().toLocaleTimeString());
  }

  function connect() {
    const ws = new WebSocket(WS_URL);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        pushEvent(payload);
        if (payload?.type === "runtime_snapshot" && payload?.payload) {
          setState((prev) => ({ ...prev, snapshot: payload.payload }));
        }
      } catch {
        pushEvent({ type: "raw_ws", payload: event.data });
      }
    };

    ws.onclose = () => setTimeout(connect, 1000);
    ws.onerror = () => setTimeout(connect, 1000);
  }

  useEffect(() => {
    connect();
    fetchControlTower();
    const timer = setInterval(fetchControlTower, 3000);
    return () => clearInterval(timer);
  }, []);

  const selected = state.topExecutable?.selected;

  return (
    <div style={{ background: "#0b1220", color: "#e8eefc", minHeight: "100vh", padding: 20, fontFamily: "Inter, system-ui, sans-serif" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap", marginBottom: 18 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 28 }}>Algotradify Control Tower</h1>
          <p style={{ ...muted, marginTop: 6, maxWidth: 820 }}>
            Runtime health, candidate truth, opportunity pipeline, execution readiness, trade quality, top executable selection, and fill lifecycle in one UI.
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <button onClick={fetchControlTower} style={{ background: "#2563eb", color: "white", border: 0, borderRadius: 8, padding: "9px 12px", fontWeight: 800 }}>
            Refresh
          </button>
          <div style={{ ...muted, fontSize: 12, marginTop: 6 }}>last refresh: {lastRefresh || "-"}</div>
        </div>
      </header>

      {errors.length ? (
        <div style={{ color: "#fecaca", background: "#3f1d1d", border: "1px solid #7f1d1d", padding: 10, borderRadius: 8, marginBottom: 16 }}>
          <strong>Backend fetch warnings:</strong> {errors.join(" | ")}
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 14, marginBottom: 14 }}>
        <Card title="Runtime">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
            <Metric label="health" value={state.health?.status || "unknown"} pill />
            <Metric label="preflight" value={state.preflight?.status || "unknown"} pill />
            <Metric label="mode" value={state.health?.mode} />
            <Metric label="market open" value={String(state.health?.market_open ?? "-")} />
          </div>
        </Card>

        <Card title="Cycle Snapshot">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
            <Metric label="stage" value={state.snapshot?.cycle_stage} />
            <Metric label="cycle ok" value={String(state.snapshot?.cycle_ok ?? "-")} />
            <Metric label="runtime executable" value={state.snapshot?.top_executable_count ?? 0} />
            <Metric label="runtime advisory" value={state.snapshot?.top_advisory_count ?? 0} />
          </div>
        </Card>

        <Card title="Tradability Summary">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
            <Metric label="real candidates" value={summary.realCandidates} />
            <Metric label="execution allowed" value={summary.executionAllowed} />
            <Metric label="blocked readiness" value={summary.blockedReadiness} />
            <Metric label="quality ranked" value={summary.qualityReady} />
          </div>
        </Card>

        <Card title="Top Executable" right={<StatusPill value={state.topExecutable?.status || "unknown"} />}>
          <Metric label="selected candidate" value={selected?.candidate_id || "none"} />
          <div style={{ height: 8 }} />
          <Metric label="quality score" value={selected?.quality_score ?? "-"} />
          <div style={{ height: 8 }} />
          <Metric label="reason" value={state.topExecutable?.reason || selected?.selection_reason || "-"} />
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 14, marginBottom: 14 }}>
        <Card title="Execution Readiness">
          <Table
            rows={safeArray(state.executionReadiness)}
            empty="no readiness records yet"
            columns={[
              { key: "candidate_id", label: "candidate" },
              { key: "status", label: "status", render: (row) => <StatusPill value={row.status} /> },
              { key: "execution_allowed", label: "allowed", render: (row) => text(row.execution_allowed) },
              { key: "blockers", label: "blockers", render: (row) => <ListChips items={row.blockers} /> },
            ]}
          />
        </Card>

        <Card title="Trade Quality">
          <Table
            rows={safeArray(state.tradeQuality)}
            empty="no quality records yet"
            columns={[
              { key: "rank", label: "rank" },
              { key: "candidate_id", label: "candidate" },
              { key: "quality_score", label: "score" },
              { key: "status", label: "status", render: (row) => <StatusPill value={row.status} /> },
              { key: "penalties", label: "penalties", render: (row) => text(row.penalties) },
            ]}
          />
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 14, marginBottom: 14 }}>
        <Card title="Candidate Truth">
          <Table
            rows={safeArray(state.candidateTruth)}
            empty="no candidate truth records yet"
            columns={[
              { key: "candidate_id", label: "candidate" },
              { key: "symbol", label: "symbol" },
              { key: "setup_family", label: "setup" },
              { key: "truth_status", label: "truth", render: (row) => <StatusPill value={row.truth_status} /> },
              { key: "blockers", label: "blockers", render: (row) => <ListChips items={row.blockers} /> },
            ]}
          />
        </Card>

        <Card title="Opportunity Layer" right={<StatusPill value={state.opportunityLayer?.status || "unknown"} />}>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
            {Object.entries(state.opportunityLayer?.counts || {}).map(([key, value]) => (
              <Metric key={key} label={key} value={value} />
            ))}
          </div>
          <Table
            rows={safeArray(state.opportunityLayer?.ranked)}
            empty="no ranked opportunity candidates yet"
            columns={[
              { key: "rank", label: "rank" },
              { key: "candidate_id", label: "candidate" },
              { key: "opportunity_status", label: "status", render: (row) => <StatusPill value={row.opportunity_status} /> },
              { key: "rank_score", label: "score" },
            ]}
          />
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 14, marginBottom: 14 }}>
        <Card title="Fill Lifecycle" right={<StatusPill value={state.fillLifecycle?.current_status || "unknown"} />}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 12 }}>
            <Metric label="candidate" value={state.fillLifecycle?.candidate_id} />
            <Metric label="terminal" value={String(state.fillLifecycle?.terminal ?? "-")} />
            <Metric label="filled qty" value={state.fillLifecycle?.filled_quantity ?? "-"} />
            <Metric label="average price" value={state.fillLifecycle?.average_price ?? "-"} />
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={muted}>blockers</div>
            <ListChips items={state.fillLifecycle?.blockers} />
          </div>
          <Table
            rows={safeArray(state.fillLifecycle?.events).slice(-8).reverse()}
            empty="no fill lifecycle evidence yet"
            columns={[
              { key: "status", label: "event", render: (row) => <StatusPill value={row.status} /> },
              { key: "ts_epoch", label: "time" },
              { key: "filled_quantity", label: "filled" },
              { key: "average_price", label: "avg price" },
            ]}
          />
        </Card>

        <Card title="Raw Runtime Opportunities">
          <Table
            rows={safeArray(state.opportunities)}
            empty="no runtime opportunities yet"
            columns={[
              { key: "symbol", label: "symbol" },
              { key: "strategy", label: "strategy" },
              { key: "bucket", label: "bucket" },
              { key: "permission", label: "permission" },
              { key: "final_action", label: "action" },
              { key: "score", label: "score" },
            ]}
          />
        </Card>
      </div>

      <Card title="Live Event Feed">
        {events.map((event, index) => (
          <div key={index} style={{ border: "1px solid #334155", padding: 10, marginBottom: 10, borderRadius: 8 }}>
            <div style={{ fontWeight: 700 }}>{event.type}</div>
            <div style={{ opacity: 0.95, wordBreak: "break-word", fontSize: 12 }}>{JSON.stringify(event.payload)}</div>
          </div>
        ))}
        {!events.length ? <div style={muted}>no websocket events yet</div> : null}
      </Card>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);

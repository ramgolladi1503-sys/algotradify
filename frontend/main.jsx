import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";

const ENV = import.meta.env || {};
const API_BASE = ENV.VITE_API_BASE_URL || ENV.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const WS_URL = ENV.VITE_WS_URL || ENV.NEXT_PUBLIC_WS_URL || API_BASE.replace(/^http/i, "ws") + "/ws";

const card = {
  background: "#121c34",
  border: "1px solid #24314f",
  borderRadius: 12,
  padding: 14,
};
const muted = { color: "#99a7c7" };

function arr(value) {
  return Array.isArray(value) ? value : [];
}

function show(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function color(value) {
  const v = String(value || "").toUpperCase();
  if (["OK", "PASS", "READY", "ALLOWED", "QUALIFIED", "SELECTED", "FILLED", "POSITION_CLOSED", "CLOSED"].includes(v)) return "#123c2c";
  if (v.includes("BLOCK") || v.includes("FAIL") || v.includes("REJECT") || v.includes("UNKNOWN")) return "#421c24";
  return "#2b2a16";
}

function Pill({ value }) {
  return (
    <span style={{ background: color(value), border: "1px solid #334155", borderRadius: 999, padding: "3px 8px", fontWeight: 800, fontSize: 12 }}>
      {show(value)}
    </span>
  );
}

function Card({ title, children, right }) {
  return (
    <section style={card}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 10 }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
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
      <div style={{ marginTop: 4, fontWeight: 800 }}>{pill ? <Pill value={value} /> : show(value)}</div>
    </div>
  );
}

function Chips({ items, empty = "none" }) {
  const values = arr(items);
  if (!values.length) return <span style={muted}>{empty}</span>;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {values.slice(0, 10).map((item, index) => (
        <span key={`${item}-${index}`} style={{ border: "1px solid #334155", borderRadius: 999, padding: "3px 8px" }}>
          {show(item)}
        </span>
      ))}
      {values.length > 10 ? <span style={muted}>+{values.length - 10} more</span> : null}
    </div>
  );
}

function Table({ rows, columns, empty }) {
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
          {rows.map((row, index) => (
            <tr key={row.candidate_id || row.id || index} style={{ borderTop: "1px solid #1f2a44" }}>
              {columns.map((column) => (
                <td key={column.key} style={{ padding: 8, verticalAlign: "top", fontSize: 13 }}>
                  {column.render ? column.render(row) : show(row[column.key])}
                </td>
              ))}
            </tr>
          ))}
          {!rows.length ? (
            <tr>
              <td style={{ padding: 10, color: "#99a7c7" }} colSpan={columns.length}>{empty}</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [events, setEvents] = useState([]);
  const [replayCandidateId, setReplayCandidateId] = useState("");
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
    outcomeReplay: null,
  });
  const [errors, setErrors] = useState([]);
  const [lastRefresh, setLastRefresh] = useState(null);

  const summary = useMemo(() => {
    const realCandidates = state.candidateTruth.filter((row) => row.truth_status === "REAL").length;
    const executionAllowed = state.executionReadiness.filter((row) => row.execution_allowed).length;
    const blockedReadiness = state.executionReadiness.filter((row) => !row.execution_allowed).length;
    const qualityReady = state.tradeQuality.filter((row) => ["QUALIFIED", "DEGRADED_BY_WARNINGS"].includes(row.status)).length;
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

  async function fetchControlTower(candidateOverride = replayCandidateId) {
    const candidateQuery = candidateOverride.trim() ? `?candidate_id=${encodeURIComponent(candidateOverride.trim())}` : "";
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
      ["outcomeReplay", `/outcome-replay${candidateQuery}`],
    ];
    const results = await Promise.allSettled(requests.map(([, path]) => fetchJson(path)));
    const next = {};
    const nextErrors = [];
    results.forEach((result, index) => {
      const [key, path] = requests[index];
      if (result.status === "fulfilled") next[key] = result.value;
      else nextErrors.push(`${path}: ${result.reason?.message || "failed"}`);
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
    const timer = setInterval(() => fetchControlTower(), 3000);
    return () => clearInterval(timer);
  }, []);

  const selected = state.topExecutable?.selected;
  const rejectedTop = arr(state.topExecutable?.rejected);
  const replayEvents = arr(state.outcomeReplay?.events).slice(-12).reverse();

  return (
    <div style={{ background: "#0b1220", color: "#e8eefc", minHeight: "100vh", padding: 20, fontFamily: "Inter, system-ui, sans-serif" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap", marginBottom: 18 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 28 }}>Algotradify Control Tower</h1>
          <p style={{ ...muted, marginTop: 6, maxWidth: 900 }}>
            Runtime health, candidate truth, opportunity pipeline, execution readiness, trade quality, top executable selection, outcome replay, blockers, warnings, and fill lifecycle in one UI.
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <button onClick={() => fetchControlTower()} style={{ background: "#2563eb", color: "white", border: 0, borderRadius: 8, padding: "9px 12px", fontWeight: 800 }}>Refresh</button>
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

        <Card title="Top Executable" right={<Pill value={state.topExecutable?.status || "unknown"} />}>
          <Metric label="selected candidate" value={selected?.candidate_id || "none"} />
          <div style={{ height: 8 }} />
          <Metric label="quality score" value={selected?.quality_score ?? "-"} />
          <div style={{ height: 8 }} />
          <Metric label="reason" value={state.topExecutable?.reason || selected?.selection_reason || "-"} />
          <div style={{ height: 10 }} />
          <div style={muted}>is_order: {show(state.topExecutable?.is_order)}</div>
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 14, marginBottom: 14 }}>
        <Card title="Outcome Replay Drilldown" right={<Pill value={state.outcomeReplay?.current_status || "unknown"} />}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end", marginBottom: 12 }}>
            <label style={{ display: "grid", gap: 4 }}>
              <span style={{ ...muted, fontSize: 12 }}>candidate_id filter</span>
              <input
                value={replayCandidateId}
                onChange={(event) => setReplayCandidateId(event.target.value)}
                placeholder="c1"
                style={{ background: "#0b1220", color: "#e8eefc", border: "1px solid #334155", borderRadius: 8, padding: "8px 10px" }}
              />
            </label>
            <button onClick={() => fetchControlTower(replayCandidateId)} style={{ background: "#2563eb", color: "white", border: 0, borderRadius: 8, padding: "9px 12px", fontWeight: 800 }}>
              Replay
            </button>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 12 }}>
            <Metric label="candidate" value={state.outcomeReplay?.candidate_id} />
            <Metric label="selected" value={state.outcomeReplay?.selected_count ?? 0} />
            <Metric label="blocked" value={state.outcomeReplay?.blocked_count ?? 0} />
            <Metric label="filled" value={state.outcomeReplay?.filled_count ?? 0} />
            <Metric label="rejected" value={state.outcomeReplay?.rejected_count ?? 0} />
            <Metric label="best quality" value={state.outcomeReplay?.best_quality_score ?? "-"} />
            <Metric label="terminal" value={String(state.outcomeReplay?.terminal ?? "-")} />
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={muted}>outcome blockers</div>
            <Chips items={state.outcomeReplay?.blockers} />
          </div>
          <div style={muted}>is_order_action: {show(state.outcomeReplay?.is_order_action)}</div>
          <Table rows={replayEvents} empty="no outcome replay events yet" columns={[
            { key: "status", label: "outcome", render: (row) => <Pill value={row.status} /> },
            { key: "ts_epoch", label: "time" },
            { key: "reason", label: "reason" },
            { key: "quality_score", label: "quality" },
            { key: "source", label: "source" },
          ]} />
        </Card>

        <Card title="Execution Readiness">
          <Table rows={arr(state.executionReadiness)} empty="no readiness records yet" columns={[
            { key: "candidate_id", label: "candidate" },
            { key: "status", label: "status", render: (row) => <Pill value={row.status} /> },
            { key: "execution_allowed", label: "allowed", render: (row) => show(row.execution_allowed) },
            { key: "blockers", label: "blockers", render: (row) => <Chips items={row.blockers} /> },
          ]} />
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 14, marginBottom: 14 }}>
        <Card title="Trade Quality">
          <Table rows={arr(state.tradeQuality)} empty="no quality records yet" columns={[
            { key: "rank", label: "rank" },
            { key: "candidate_id", label: "candidate" },
            { key: "quality_score", label: "quality_score" },
            { key: "status", label: "status", render: (row) => <Pill value={row.status} /> },
            { key: "penalties", label: "penalties", render: (row) => show(row.penalties) },
          ]} />
        </Card>

        <Card title="Top Executable Rejections">
          <Table rows={rejectedTop} empty="no selector rejections" columns={[
            { key: "candidate_id", label: "candidate" },
            { key: "quality_score", label: "score" },
            { key: "selector_rejection_reasons", label: "selector_rejection_reasons", render: (row) => <Chips items={row.selector_rejection_reasons} /> },
            { key: "blockers", label: "blockers", render: (row) => <Chips items={row.blockers} /> },
          ]} />
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 14, marginBottom: 14 }}>
        <Card title="Candidate Truth">
          <Table rows={arr(state.candidateTruth)} empty="no candidate truth records yet" columns={[
            { key: "candidate_id", label: "candidate" },
            { key: "symbol", label: "symbol" },
            { key: "setup_family", label: "setup" },
            { key: "truth_status", label: "truth", render: (row) => <Pill value={row.truth_status} /> },
            { key: "blockers", label: "blockers", render: (row) => <Chips items={row.blockers} /> },
          ]} />
        </Card>

        <Card title="Opportunity Layer" right={<Pill value={state.opportunityLayer?.status || "unknown"} />}>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
            {Object.entries(state.opportunityLayer?.counts || {}).map(([key, value]) => <Metric key={key} label={key} value={value} />)}
          </div>
          <Table rows={arr(state.opportunityLayer?.ranked)} empty="no ranked opportunity candidates yet" columns={[
            { key: "rank", label: "rank" },
            { key: "candidate_id", label: "candidate" },
            { key: "opportunity_status", label: "status", render: (row) => <Pill value={row.opportunity_status} /> },
            { key: "rank_score", label: "score" },
          ]} />
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 14, marginBottom: 14 }}>
        <Card title="Fill Lifecycle" right={<Pill value={state.fillLifecycle?.current_status || "unknown"} />}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 12 }}>
            <Metric label="candidate" value={state.fillLifecycle?.candidate_id} />
            <Metric label="terminal" value={String(state.fillLifecycle?.terminal ?? "-")} />
            <Metric label="filled qty" value={state.fillLifecycle?.filled_quantity ?? "-"} />
            <Metric label="average price" value={state.fillLifecycle?.average_price ?? "-"} />
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={muted}>blockers</div>
            <Chips items={state.fillLifecycle?.blockers} />
          </div>
          <div style={muted}>is_order_submission: {show(state.fillLifecycle?.is_order_submission)}</div>
          <Table rows={arr(state.fillLifecycle?.events).slice(-8).reverse()} empty="no fill lifecycle evidence yet" columns={[
            { key: "status", label: "event", render: (row) => <Pill value={row.status} /> },
            { key: "ts_epoch", label: "time" },
            { key: "filled_quantity", label: "filled" },
            { key: "average_price", label: "avg price" },
          ]} />
        </Card>

        <Card title="Raw Runtime Opportunities">
          <Table rows={arr(state.opportunities)} empty="no runtime opportunities yet" columns={[
            { key: "symbol", label: "symbol" },
            { key: "strategy", label: "strategy" },
            { key: "bucket", label: "bucket" },
            { key: "permission", label: "permission" },
            { key: "final_action", label: "action" },
            { key: "score", label: "score" },
          ]} />
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

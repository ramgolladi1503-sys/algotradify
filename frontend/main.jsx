import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  BarChart,
  Card,
  Chips,
  DryRunEvidenceExportPreviewCard,
  DryRunExecutionAdapterCard,
  EvidenceHealthPanel,
  ExecutionSafetyCard,
  Metric,
  OutcomeReplayDrilldownCard,
  Pill,
  Table,
  arr,
  show,
} from './controlTowerCards.jsx';

const ENV = import.meta.env || {};
const API_BASE = ENV.VITE_API_BASE_URL || ENV.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
const WS_URL = ENV.VITE_WS_URL || ENV.NEXT_PUBLIC_WS_URL || API_BASE.replace(/^http/i, 'ws') + '/ws';
const PERSISTED_PREFS_KEY = 'algotradify.controlTower.preferences.v1';
const DEFAULT_FILTERS = { query: '', status: 'all', minQuality: 0 };
const DEFAULT_REPLAY_QUERY = { candidateId: '', status: '', strategy: '', tsFromEpoch: '', tsToEpoch: '' };
const OPERATOR_VIEWS = {
  default: { label: 'Default view', filters: DEFAULT_FILTERS },
  blocked: { label: 'Blocked focus', filters: { query: '', status: 'blocked', minQuality: 0 } },
  ready: { label: 'Trade-ready focus', filters: { query: '', status: 'allowed', minQuality: 70 } },
  replay: { label: 'Replay focus', filters: DEFAULT_FILTERS },
  lifecycle: { label: 'Lifecycle focus', filters: DEFAULT_FILTERS },
};
const DEFAULT_PREFS = { filters: DEFAULT_FILTERS, replayQuery: DEFAULT_REPLAY_QUERY, operatorView: 'default' };
const muted = { color: '#99a7c7' };

function normalizeReplayQuery(raw = {}) {
  return {
    candidateId: String(raw.candidateId ?? raw.candidate_id ?? ''),
    status: String(raw.status || ''),
    strategy: String(raw.strategy || ''),
    tsFromEpoch: String(raw.tsFromEpoch ?? raw.ts_from_epoch ?? ''),
    tsToEpoch: String(raw.tsToEpoch ?? raw.ts_to_epoch ?? ''),
  };
}
function loadPersistedPreferences() { if (typeof window === 'undefined') return DEFAULT_PREFS; try { const p = JSON.parse(window.localStorage.getItem(PERSISTED_PREFS_KEY) || '{}'); const legacyReplayKey = `replay${'CandidateId'}`; const replayQuery = normalizeReplayQuery(p.replayQuery || { candidateId: p[legacyReplayKey] || '' }); return { filters: { ...DEFAULT_FILTERS, ...(p.filters || {}) }, replayQuery, operatorView: p.operatorView || 'default' }; } catch { return DEFAULT_PREFS; } }
function savePersistedPreferences(p) { if (typeof window !== 'undefined') window.localStorage.setItem(PERSISTED_PREFS_KEY, JSON.stringify(p)); }
function clearPersistedPreferences() { if (typeof window !== 'undefined') window.localStorage.removeItem(PERSISTED_PREFS_KEY); }
function statusText(row) { return String(row?.status || row?.truth_status || row?.opportunity_status || row?.current_status || row?.bucket || '').toUpperCase(); }
function isBlocked(row) { return statusText(row).includes('BLOCK') || statusText(row).includes('REJECT') || row?.execution_allowed === false || arr(row?.blockers).length > 0; }
function isSelected(row) { return statusText(row).includes('SELECT') || row?.selected === true; }
function isAllowed(row) { return row?.execution_allowed === true || row?.execution_permitted === true || ['ALLOWED', 'QUALIFIED', 'PERMITTED'].includes(statusText(row)); }
function applyFilters(rows, filters) { const q = filters.query.trim().toLowerCase(); return arr(rows).filter((r) => (!q || JSON.stringify(r).toLowerCase().includes(q)) && (filters.status !== 'blocked' || isBlocked(r)) && (filters.status !== 'selected' || isSelected(r)) && (filters.status !== 'allowed' || isAllowed(r)) && (filters.status !== 'rejected' || statusText(r).includes('REJECT'))); }
function buttonStyle(active = false) { return { background: active ? '#2563eb' : '#334155', color: 'white', border: 0, borderRadius: 8, padding: '9px 12px', fontWeight: 800 }; }
function buildReplayQueryString(replayQuery = DEFAULT_REPLAY_QUERY) {
  const params = new URLSearchParams();
  const q = normalizeReplayQuery(replayQuery);
  if (q.candidateId.trim()) params.set('candidate_id', q.candidateId.trim());
  if (q.status.trim()) params.set('status', q.status.trim());
  if (q.strategy.trim()) params.set('strategy', q.strategy.trim());
  if (q.tsFromEpoch.trim()) params.set('ts_from_epoch', q.tsFromEpoch.trim());
  if (q.tsToEpoch.trim()) params.set('ts_to_epoch', q.tsToEpoch.trim());
  const query = params.toString();
  return query ? `?${query}` : '';
}
function replayCandidateKey(row) { return String(row?.candidate_id || row?.trade_id || 'unknown'); }
function replayStatus(row) { return String(row?.outcome_status || row?.status || row?.event || row?.current_status || 'UNKNOWN').toUpperCase(); }
function replayStrategy(row) { const evidence = row?.evidence && typeof row.evidence === 'object' ? row.evidence : {}; const selected = row?.selected && typeof row.selected === 'object' ? row.selected : {}; return row?.strategy || row?.strategy_id || row?.strategy_family || row?.setup_family || evidence.strategy_family || evidence.strategy || selected.strategy_family || selected.strategy || 'UNKNOWN'; }
function replayTimestampNumber(row) { const raw = row?.ts_epoch ?? row?.timestamp ?? row?.time ?? row?.created_at; const parsed = Number(raw); return Number.isFinite(parsed) ? parsed : null; }
function replayQualityScore(row) { const parsed = Number(row?.quality_score ?? row?.trade_quality_score ?? row?.score); return Number.isFinite(parsed) ? parsed : null; }
function replayDistribution(values) { const counts = new Map(); values.forEach((value) => counts.set(value, (counts.get(value) || 0) + 1)); return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).map(([label, value]) => `${label}: ${value}`); }
function replayAnalyticsSummary(events) { const rows = arr(events); const timestamps = rows.map(replayTimestampNumber).filter((value) => value !== null); const scores = rows.map(replayQualityScore).filter((value) => value !== null); return { candidateCount: new Set(rows.map(replayCandidateKey)).size, eventCount: rows.length, statusDistribution: replayDistribution(rows.map(replayStatus)), strategyDistribution: replayDistribution(rows.map(replayStrategy)), timeWindowMin: timestamps.length ? Math.min(...timestamps) : null, timeWindowMax: timestamps.length ? Math.max(...timestamps) : null, bestQualityScore: scores.length ? Math.max(...scores) : null, worstQualityScore: scores.length ? Math.min(...scores) : null }; }
function ReplayAnalyticsSummaryPanel({ events }) { const summary = replayAnalyticsSummary(events); return <Card title='Replay Analytics Summary Panel' right={<Pill value='READ_ONLY_ANALYTICS' />}><p style={muted}>Read-only replay analytics derived from the active filtered replay result set.</p><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 8 }}><Metric label='candidate_count' value={summary.candidateCount} /><Metric label='event_count' value={summary.eventCount} /><Metric label='time_window_min' value={summary.timeWindowMin} /><Metric label='time_window_max' value={summary.timeWindowMax} /><Metric label='best_quality_score' value={summary.bestQualityScore} /><Metric label='worst_quality_score' value={summary.worstQualityScore} /></div><div>status distribution</div><Chips items={summary.statusDistribution} /><div>strategy distribution</div><Chips items={summary.strategyDistribution} /></Card>; }

function App() {
  const initialPrefs = loadPersistedPreferences();
  const [events, setEvents] = useState([]);
  const [filters, setFilters] = useState(initialPrefs.filters);
  const [replayQuery, setReplayQuery] = useState(initialPrefs.replayQuery);
  const [operatorView, setOperatorView] = useState(initialPrefs.operatorView);
  const [state, setState] = useState({ health: null, preflight: null, snapshot: null, opportunities: [], candidateTruth: [], opportunityLayer: null, executionReadiness: [], tradeQuality: [], topExecutable: null, executionSafety: null, dryRunExecution: null, dryRunExport: null, evidenceHealth: null, fillLifecycle: null, outcomeReplay: null });
  useEffect(() => savePersistedPreferences({ filters, replayQuery, operatorView }), [filters, replayQuery, operatorView]);
  async function fetchJson(path) { const r = await fetch(`${API_BASE}${path}`); if (!r.ok) throw new Error(path); return r.json(); }
  async function fetchControlTower(replayOverride = replayQuery) { const replayQueryString = buildReplayQueryString(replayOverride); const requests = [['health', '/runtime/health'], ['preflight', '/runtime/preflight'], ['snapshot', '/runtime/snapshot'], ['opportunities', '/opportunities?limit=20'], ['candidateTruth', '/candidate-truth?limit=20'], ['opportunityLayer', '/opportunity-layer?limit=20'], ['executionReadiness', '/execution-readiness?limit=20'], ['tradeQuality', '/trade-quality?limit=20'], ['topExecutable', '/top-executable?limit=20'], ['executionSafety', '/execution-safety?limit=20'], ['dryRunExecution', '/dry-run-execution?limit=20'], ['dryRunExport', '/dry-run-execution/export?limit=20'], ['evidenceHealth', '/evidence-health?limit=20'], ['fillLifecycle', '/fill-lifecycle'], ['outcomeReplay', `/outcome-replay${replayQueryString}`]]; const results = await Promise.allSettled(requests.map(([, p]) => fetchJson(p))); const next = {}; results.forEach((r, i) => { if (r.status === 'fulfilled') next[requests[i][0]] = r.value; }); setState((p) => ({ ...p, ...next })); }
  function connect() { const ws = new WebSocket(WS_URL); ws.onmessage = (event) => { try { const payload = JSON.parse(event.data); setEvents((p) => [payload, ...p.slice(0, 80)]); if (payload?.type === 'runtime_snapshot' && payload?.payload) setState((p) => ({ ...p, snapshot: payload.payload })); } catch { setEvents((p) => [{ type: 'raw_ws', payload: event.data }, ...p.slice(0, 80)]); } }; ws.onclose = () => setTimeout(connect, 1000); ws.onerror = () => setTimeout(connect, 1000); }
  useEffect(() => { connect(); fetchControlTower(); const t = setInterval(() => fetchControlTower(), 3000); return () => clearInterval(t); }, []);
  function resetToDefaultView() { clearPersistedPreferences(); setOperatorView('default'); setFilters(DEFAULT_FILTERS); setReplayQuery(DEFAULT_REPLAY_QUERY); }
  function applyOperatorView(k) { setOperatorView(k); setFilters({ ...(OPERATOR_VIEWS[k] || OPERATOR_VIEWS.default).filters }); }
  function updateReplayQuery(patch) { setReplayQuery((p) => ({ ...p, ...patch })); }
  function resetReplayQuery() { const next = DEFAULT_REPLAY_QUERY; setReplayQuery(next); fetchControlTower(next); }

  const selected = state.topExecutable?.selected;
  const filtered = useMemo(() => ({ opportunities: applyFilters(state.opportunities, filters), candidateTruth: applyFilters(state.candidateTruth, filters), executionReadiness: applyFilters(state.executionReadiness, filters), tradeQuality: applyFilters(state.tradeQuality, filters), topRejected: applyFilters(state.topExecutable?.rejected || [], filters), outcomeEvents: applyFilters(arr(state.outcomeReplay?.events), filters) }), [state, filters]);
  const analytics = { readinessBreakdown: [], qualityDistribution: [], outcomeCounts: [], truthBreakdown: [] };

  return <div style={{ background: '#0b1220', color: '#e8eefc', minHeight: '100vh', padding: 20 }}><h1>Algotradify Control Tower</h1><p style={muted}>Runtime health, persisted UI preferences, execution safety, dry-run evidence, export preview, evidence health, replay timeline query filters, analytics charts, replay drilldowns, and lifecycle evidence.</p>
    <Card title='Operator Views'>{Object.entries(OPERATOR_VIEWS).map(([k, v]) => <button key={k} onClick={() => applyOperatorView(k)} style={buttonStyle(operatorView === k)}>{v.label}</button>)} <button onClick={resetToDefaultView}>Reset to default view</button><span> Persisted UI Preferences</span></Card>
    <Card title='Frontend Filters'><span>candidate search/filter</span><input value={filters.query} onChange={(e) => setFilters((p) => ({ ...p, query: e.target.value }))} /><span>status filter</span><select value={filters.status} onChange={(e) => setFilters((p) => ({ ...p, status: e.target.value }))}><option value='all'>all</option><option value='blocked'>blocked-only view</option><option value='selected'>selected-only view</option><option value='allowed'>allowed-only view</option><option value='rejected'>rejected-only view</option></select><span>quality score threshold filter</span><button onClick={() => setFilters(DEFAULT_FILTERS)}>Reset filters</button></Card>
    <Card title='Runtime'><Metric label='health' value={state.health?.status} /><Metric label='preflight' value={state.preflight?.status} /></Card><Card title='Cycle Snapshot'><Metric label='stage' value={state.snapshot?.cycle_stage} /></Card><Card title='Tradability Summary'><Metric label='real candidates' value={filtered.candidateTruth.length} /></Card><Card title='Top Executable' right={<Pill value={state.topExecutable?.status} />}><Metric label='selected candidate' value={selected?.candidate_id} /><Metric label='quality_score' value={selected?.quality_score} /><div>is_order: {show(state.topExecutable?.is_order)}</div></Card>
    <ExecutionSafetyCard executionSafety={state.executionSafety} />
    <DryRunExecutionAdapterCard dryRunExecution={state.dryRunExecution} topExecutable={state.topExecutable} executionSafety={state.executionSafety} />
    <DryRunEvidenceExportPreviewCard dryRunExport={state.dryRunExport} />
    <EvidenceHealthPanel evidenceHealth={state.evidenceHealth} />
    <BarChart title='Readiness Breakdown Chart' data={analytics.readinessBreakdown} /><BarChart title='Outcome Counts Chart' data={analytics.outcomeCounts} /><BarChart title='Quality Score Distribution Chart' data={analytics.qualityDistribution} /><BarChart title='Candidate Truth Breakdown Chart' data={analytics.truthBreakdown} />
    <ReplayAnalyticsSummaryPanel events={filtered.outcomeEvents} />
    <OutcomeReplayDrilldownCard outcomeReplay={state.outcomeReplay} replayQuery={replayQuery} updateReplayQuery={updateReplayQuery} fetchControlTower={fetchControlTower} resetReplayQuery={resetReplayQuery} filteredOutcomeEvents={filtered.outcomeEvents} />
    <Card title='Execution Readiness'><Table rows={filtered.executionReadiness} empty='no readiness records match filters' /></Card><Card title='Trade Quality'><Table rows={filtered.tradeQuality} empty='no quality records match filters' /></Card><Card title='Top Executable Rejections'><div>selector_rejection_reasons</div><Table rows={filtered.topRejected} empty='no selector rejections match filters' /></Card><Card title='Candidate Truth'><Table rows={filtered.candidateTruth} empty='no candidate truth records match filters' /></Card><Card title='Opportunity Layer'><Table rows={applyFilters(state.opportunityLayer?.ranked || [], filters)} empty='no ranked opportunity candidates match filters' /></Card><Card title='Fill Lifecycle'><div>is_order_submission: {show(state.fillLifecycle?.is_order_submission)}</div><Table rows={arr(state.fillLifecycle?.events)} empty='no fill lifecycle evidence matches filters' /></Card><Card title='Raw Runtime Opportunities'><Table rows={filtered.opportunities} empty='no runtime opportunities match filters' /></Card>
    <Card title='Live Event Feed'>{events.length ? events.map((e, i) => <pre key={i}>{JSON.stringify(e.payload)}</pre>) : <div>no websocket events yet</div>}</Card>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);

import React from 'react';

const card = { background: '#121c34', border: '1px solid #24314f', borderRadius: 12, padding: 14, marginBottom: 14 };
const muted = { color: '#99a7c7' };

export function arr(v) { return Array.isArray(v) ? v : []; }
export function show(v) { if (v === null || v === undefined || v === '') return '-'; if (typeof v === 'object') return JSON.stringify(v); return String(v); }

export function Pill({ value }) {
  return <span style={{ background: String(value).includes('BLOCK') || String(value).includes('UNSAFE') ? '#421c24' : '#123c2c', borderRadius: 999, padding: '3px 8px', fontWeight: 800 }}>{show(value)}</span>;
}

export function Card({ title, children, right }) {
  return <section style={card}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}><h3 style={{ margin: 0 }}>{title}</h3>{right}</div>{children}</section>;
}

export function Metric({ label, value, danger = false }) {
  return <div style={{ minWidth: 130, margin: 6, color: danger ? '#fecaca' : 'inherit' }}><div style={{ ...muted, fontSize: 12 }}>{label}</div><strong>{show(value)}</strong></div>;
}

export function Chips({ items }) {
  const values = arr(items);
  return values.length ? <div>{values.map((x, i) => <span key={i} style={{ border: '1px solid #334155', borderRadius: 999, padding: '3px 8px', marginRight: 6 }}>{show(x)}</span>)}</div> : <span style={muted}>none</span>;
}

export function JsonBlock({ title, value }) {
  return <details style={{ border: '1px solid #334155', borderRadius: 10, padding: 10, background: '#0b1220' }}><summary>{title}</summary><pre>{JSON.stringify(value || {}, null, 2)}</pre></details>;
}

export function CompactSnapshot(props) {
  return <JsonBlock {...props} />;
}

export function Table({ rows, empty }) {
  return arr(rows).length ? <pre>{JSON.stringify(rows.slice(0, 10), null, 2)}</pre> : <div style={muted}>{empty}</div>;
}

export function BarChart({ title, data = [] }) {
  return <Card title={title}>{data.length ? data.map((r) => <div key={r.label}>{r.label}: {r.value}</div>) : <div style={muted}>no analytics yet</div>}</Card>;
}

export function dryRunExplanation(dryRun) {
  if (!dryRun) return 'Dry-run evidence unavailable.';
  if (dryRun.created) return 'Dry-run intent is created from the selected candidate, execution safety decision, approval evidence, and readiness snapshot. This is still local simulation evidence only.';
  const blockers = arr(dryRun.blockers);
  if (blockers.length) return `Dry-run is blocked because: ${blockers.join(', ')}. Resolve the upstream evidence before moving forward.`;
  return 'Dry-run is not created yet. Check top executable, safety, approval, and readiness evidence.';
}

export function exportBundles(v) {
  if (!v) return [];
  if (Array.isArray(v)) return v;
  if (Array.isArray(v.bundles)) return v.bundles;
  if (Array.isArray(v.items)) return v.items;
  return typeof v === 'object' ? [v] : [];
}

export function exportFlagWarnings(bundle) {
  const w = [];
  if (bundle.dry_run_only !== true) w.push('dry_run_only is not true');
  if (bundle.is_order_action !== false) w.push('is_order_action is not false');
  if (bundle.broker_api_called !== false) w.push('broker_api_called is not false');
  if (bundle.real_order_id !== null && bundle.real_order_id !== undefined) w.push('real_order_id is not null');
  if (bundle.export_preview_only !== true) w.push('export_preview_only is not true');
  return w;
}

export function ExecutionSafetyCard({ executionSafety }) {
  return <Card title='Execution Safety'><Metric label='execution_permitted' value={executionSafety?.execution_permitted} /><Metric label='requires_manual_approval' value={executionSafety?.requires_manual_approval} /><Metric label='readiness_records_checked' value={executionSafety?.readiness_records_checked} /><Metric label='safety_visibility_only' value={executionSafety?.safety_visibility_only} /><div>safety blockers</div><Chips items={executionSafety?.blockers} /><div>safety warnings</div><Chips items={executionSafety?.warnings} /><div>is_order_action: {show(executionSafety?.is_order_action)}</div></Card>;
}

export function DryRunExecutionAdapterCard({ dryRunExecution, topExecutable, executionSafety }) {
  const dryRun = dryRunExecution || {};
  const dryRunIntent = dryRun.intent || {};
  const selectedCandidateSnapshot = dryRunIntent.top_executable_snapshot || dryRun.top_executable_snapshot || topExecutable || {};
  const executionSafetySnapshot = dryRunIntent.execution_safety_snapshot || dryRun.execution_safety_snapshot || executionSafety || {};
  const approvalSnapshot = dryRunIntent.approval_snapshot || dryRun.approval_snapshot || {};
  const readinessSnapshot = dryRunIntent.readiness_snapshot || dryRun.readiness_snapshot || {};
  const outcomeEvent = dryRun.outcome_event || {};
  return <Card title='Dry-Run Execution Adapter'><Metric label='dry_run_only' value={dryRun.dry_run_only} /><Metric label='is_order_action' value={dryRun.is_order_action} /><Metric label='broker_api_called' value={dryRun.broker_api_called} /><Metric label='dry_run_order_id' value={dryRunIntent.dry_run_order_id} /><Metric label='real_order_id' value={dryRunIntent.real_order_id} /><div>dry-run blockers</div><Chips items={dryRun.blockers} /><div>dry-run warnings</div><Chips items={dryRun.warnings} /><strong>Dry-run operator explanation</strong><p>{dryRunExplanation(dryRun)}</p><JsonBlock title='selected candidate snapshot' value={selectedCandidateSnapshot} /><JsonBlock title='execution safety snapshot' value={executionSafetySnapshot} /><JsonBlock title='approval snapshot' value={approvalSnapshot} /><JsonBlock title='readiness snapshot' value={readinessSnapshot} /><JsonBlock title='outcome event' value={outcomeEvent} /><div>Preview Dry Run uses /dry-run-execution?limit=20 only. Control Tower never calls append from the frontend.</div></Card>;
}

export function DryRunEvidenceExportPreviewCard({ dryRunExport }) {
  const exportPreviewBundles = exportBundles(dryRunExport);
  return <Card title='Dry-Run Evidence Export Preview' right={<Pill value={exportPreviewBundles[0]?.status || 'NO_EXPORT_BUNDLE'} />}><p>Read-only preview from /dry-run-execution/export?limit=20. No execution controls, no broker calls, and no server-side file append is requested.</p>{exportPreviewBundles.map((bundle, i) => { const unsafe = exportFlagWarnings(bundle); return <div key={i}><Pill value={unsafe.length ? 'UNSAFE_FLAG_WARNING' : bundle.status} /><Metric label='bundle_type' value={bundle.bundle_type} /><Metric label='status' value={bundle.status} /><Metric label='candidate_id' value={bundle.candidate_id} /><Metric label='dry_run_order_id' value={bundle.dry_run_order_id} /><Metric label='dry_run_only' value={bundle.dry_run_only} danger={bundle.dry_run_only !== true} /><Metric label='is_order_action' value={bundle.is_order_action} danger={bundle.is_order_action !== false} /><Metric label='broker_api_called' value={bundle.broker_api_called} danger={bundle.broker_api_called !== false} /><Metric label='real_order_id' value={bundle.real_order_id} danger={bundle.real_order_id !== null && bundle.real_order_id !== undefined} /><Metric label='export_preview_only' value={bundle.export_preview_only} danger={bundle.export_preview_only !== true} /><div>blockers</div><Chips items={bundle.blockers} /><div>warnings</div><Chips items={bundle.warnings} /><CompactSnapshot title='selected snapshot' value={bundle.selected_candidate_snapshot} /><CompactSnapshot title='safety snapshot' value={bundle.execution_safety_snapshot} /><CompactSnapshot title='approval snapshot' value={bundle.approval_snapshot} /><CompactSnapshot title='readiness snapshot' value={bundle.readiness_snapshot} /></div>; })}</Card>;
}

export function OutcomeReplayDrilldownCard({ outcomeReplay, replayCandidateId, setReplayCandidateId, fetchControlTower, filteredOutcomeEvents }) {
  return <Card title='Outcome Replay Drilldown'><input placeholder='candidate_id filter' value={replayCandidateId} onChange={(e) => setReplayCandidateId(e.target.value)} /><button onClick={() => fetchControlTower(replayCandidateId)}>Replay</button><Metric label='selected_count' value={outcomeReplay?.selected_count} /><Metric label='blocked_count' value={outcomeReplay?.blocked_count} /><Metric label='filled_count' value={outcomeReplay?.filled_count} /><Metric label='rejected_count' value={outcomeReplay?.rejected_count} /><Metric label='best_quality_score' value={outcomeReplay?.best_quality_score} /><div>outcome blockers</div><Chips items={outcomeReplay?.blockers} /><Table rows={filteredOutcomeEvents} empty='no outcome replay events yet' /></Card>;
}

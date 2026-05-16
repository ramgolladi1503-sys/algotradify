import React from 'react';

const card = { background: '#121c34', border: '1px solid #24314f', borderRadius: 12, padding: 14, marginBottom: 14 };
const muted = { color: '#99a7c7' };
const flagGrid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 8, margin: '10px 0' };
const formGrid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 10, margin: '10px 0' };
const subtlePanel = { border: '1px solid #334155', borderRadius: 10, padding: 10, background: '#0b1220', margin: '10px 0' };
const warningPanel = { border: '1px solid #7f1d1d', borderRadius: 10, padding: 10, background: '#3f1d1d', margin: '10px 0', color: '#fecaca' };
const safePanel = { border: '1px solid #14532d', borderRadius: 10, padding: 10, background: '#052e16', margin: '10px 0' };
const fieldStyle = { width: '100%', boxSizing: 'border-box', borderRadius: 8, border: '1px solid #334155', background: '#0b1220', color: '#e8eefc', padding: 8 };

export function arr(v) { return Array.isArray(v) ? v : []; }
export function show(v) { if (v === null || v === undefined || v === '') return '-'; if (typeof v === 'object') return JSON.stringify(v); return String(v); }

export function Pill({ value }) {
  return <span style={{ background: String(value).includes('BLOCK') || String(value).includes('UNSAFE') || String(value).includes('DEGRADED') ? '#421c24' : '#123c2c', borderRadius: 999, padding: '3px 8px', fontWeight: 800 }}>{show(value)}</span>;
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

export function exportPreviewStatus(bundle) {
  if (!bundle) return 'NO_EXPORT_BUNDLE';
  if (exportFlagWarnings(bundle).length) return 'UNSAFE_FLAG_WARNING';
  if (String(bundle.status || '').includes('BLOCK')) return 'EXPORT_BUNDLE_BLOCKED';
  return 'SAFE_EXPORT_FLAGS';
}

function FlagCheckMetric({ label, value, expected }) {
  const safe = value === expected || (expected === null && (value === null || value === undefined));
  return <div style={{ ...subtlePanel, borderColor: safe ? '#14532d' : '#7f1d1d' }}><div style={{ ...muted, fontSize: 12 }}>{label}</div><strong>{show(value)}</strong><div style={{ fontSize: 12, color: safe ? '#bbf7d0' : '#fecaca' }}>{safe ? 'safe expected flag' : 'unsafe flag mismatch'}</div></div>;
}

function ExportBundleState({ bundle }) {
  const unsafe = exportFlagWarnings(bundle);
  const blocked = String(bundle.status || '').includes('BLOCK') || arr(bundle.blockers).length > 0;
  if (unsafe.length) return <div style={warningPanel}><strong>UNSAFE_FLAG_WARNING</strong><div>Export preview is read-only, but these flags are not safe: {unsafe.join(', ')}</div></div>;
  if (blocked) return <div style={warningPanel}><strong>Export bundle blocked</strong><div>The evidence bundle is blocked or incomplete. This is still safe because the preview remains read-only and no broker action is exposed.</div></div>;
  return <div style={safePanel}><strong>Why this bundle is safe</strong><div>This bundle is safe because dry_run_only is true, is_order_action is false, broker_api_called is false, real_order_id is null, and export_preview_only is true.</div></div>;
}

function ExportFlagChecks({ bundle }) {
  return <div><h4>Expected safe flags</h4><div style={flagGrid}><FlagCheckMetric label='dry_run_only' value={bundle.dry_run_only} expected={true} /><FlagCheckMetric label='is_order_action' value={bundle.is_order_action} expected={false} /><FlagCheckMetric label='broker_api_called' value={bundle.broker_api_called} expected={false} /><FlagCheckMetric label='real_order_id' value={bundle.real_order_id} expected={null} /><FlagCheckMetric label='export_preview_only' value={bundle.export_preview_only} expected={true} /></div></div>;
}

function evidenceHealthRows(evidenceHealth) {
  const results = evidenceHealth?.results || {};
  return Object.entries(results).map(([schemaId, result]) => ({ schemaId, result }));
}

function replayQueryMetadata(outcomeReplay) {
  return outcomeReplay?.query || {};
}

function ReplayQueryField({ label, value, onChange, placeholder }) {
  return <label><div style={{ ...muted, fontSize: 12 }}>{label}</div><input style={fieldStyle} placeholder={placeholder} value={value || ''} onChange={(e) => onChange(e.target.value)} /></label>;
}

function ReplayTimelineMetadata({ query }) {
  const unsafe = query.read_only !== true || query.is_order_action !== false;
  return <div style={unsafe ? warningPanel : safePanel}><strong>Replay query metadata</strong><div style={flagGrid}><Metric label='source_count' value={query.source_count} /><Metric label='result_count' value={query.result_count} /><Metric label='read_only' value={query.read_only} danger={query.read_only !== true} /><Metric label='is_order_action' value={query.is_order_action} danger={query.is_order_action !== false} /></div>{unsafe ? <div>Replay metadata is not safe. Do not use this result for execution.</div> : <div>Replay query is read-only and is_order_action=false.</div>}</div>;
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
  return <Card title='Dry-Run Evidence Export Preview' right={<Pill value={exportPreviewStatus(exportPreviewBundles[0])} />}><p>Read-only preview from /dry-run-execution/export?limit=20. No execution controls, no broker calls, and no server-side file append is requested.</p>{!exportPreviewBundles.length ? <div style={subtlePanel}><strong>No export bundle returned yet</strong><div style={muted}>The preview is waiting for dry-run evidence. This card stays read-only and exposes no order controls.</div></div> : null}{exportPreviewBundles.map((bundle, i) => { const unsafe = exportFlagWarnings(bundle); return <div key={i} style={subtlePanel}><Pill value={unsafe.length ? 'UNSAFE_FLAG_WARNING' : exportPreviewStatus(bundle)} /><div style={flagGrid}><Metric label='bundle_type' value={bundle.bundle_type} /><Metric label='status' value={bundle.status} /><Metric label='candidate_id' value={bundle.candidate_id} /><Metric label='dry_run_order_id' value={bundle.dry_run_order_id} /></div><ExportBundleState bundle={bundle} /><ExportFlagChecks bundle={bundle} /><div>blockers</div><Chips items={bundle.blockers} /><div>warnings</div><Chips items={bundle.warnings} /><details style={subtlePanel}><summary>Snapshot drilldowns</summary><CompactSnapshot title='selected snapshot' value={bundle.selected_candidate_snapshot} /><CompactSnapshot title='safety snapshot' value={bundle.execution_safety_snapshot} /><CompactSnapshot title='approval snapshot' value={bundle.approval_snapshot} /><CompactSnapshot title='readiness snapshot' value={bundle.readiness_snapshot} /></details></div>; })}</Card>;
}

export function EvidenceHealthPanel({ evidenceHealth }) {
  const rows = evidenceHealthRows(evidenceHealth);
  return <Card title='Evidence Health Panel' right={<Pill value={evidenceHealth?.status || 'NO_EVIDENCE_HEALTH'} />}><p>Read-only integrity view from /evidence-health?limit=20. This panel validates evidence shape and safe flags only; it exposes no execution controls.</p><div style={flagGrid}><Metric label='evidence_health_only' value={evidenceHealth?.evidence_health_only} danger={evidenceHealth?.evidence_health_only !== true} /><Metric label='dry_run_only' value={evidenceHealth?.dry_run_only} danger={evidenceHealth?.dry_run_only !== true} /><Metric label='is_order_action' value={evidenceHealth?.is_order_action} danger={evidenceHealth?.is_order_action !== false} /><Metric label='broker_api_called' value={evidenceHealth?.broker_api_called} danger={evidenceHealth?.broker_api_called !== false} /><Metric label='real_order_id' value={evidenceHealth?.real_order_id} danger={evidenceHealth?.real_order_id !== null && evidenceHealth?.real_order_id !== undefined} /><Metric label='schema_count' value={evidenceHealth?.schema_count} /><Metric label='valid_count' value={evidenceHealth?.valid_count} /><Metric label='invalid_count' value={evidenceHealth?.invalid_count} danger={(evidenceHealth?.invalid_count || 0) > 0} /><Metric label='missing_key_count' value={evidenceHealth?.missing_key_count} danger={(evidenceHealth?.missing_key_count || 0) > 0} /><Metric label='safe_flag_violation_count' value={evidenceHealth?.safe_flag_violation_count} danger={(evidenceHealth?.safe_flag_violation_count || 0) > 0} /><Metric label='warning_count' value={evidenceHealth?.warning_count} danger={(evidenceHealth?.warning_count || 0) > 0} /></div>{!rows.length ? <div style={subtlePanel}><strong>No evidence health returned yet</strong><div style={muted}>The panel is waiting for read-only integrity results.</div></div> : null}{rows.map(({ schemaId, result }) => <details key={schemaId} style={result.valid ? safePanel : warningPanel}><summary>{schemaId}: {result.valid ? 'valid' : 'invalid'}</summary><div>missing_keys</div><Chips items={result.missing_keys} /><div>safe_flag_violations</div><Chips items={(result.safe_flag_violations || []).map((row) => `${row.key}: expected ${show(row.expected)}, actual ${show(row.actual)}`)} /><div>warnings</div><Chips items={result.warnings} /></details>)}</Card>;
}

export function OutcomeReplayDrilldownCard({ outcomeReplay, replayQuery, updateReplayQuery, fetchControlTower, resetReplayQuery, filteredOutcomeEvents }) {
  const q = replayQuery || {};
  const metadata = replayQueryMetadata(outcomeReplay);
  return <Card title='Replay Timeline UI' right={<Pill value='READ_ONLY_REPLAY_TIMELINE' />}><p>Read-only replay timeline from /outcome-replay. Filters are query-only and expose no broker calls, no real orders, no submit/modify/cancel/exit controls, and no append=true behavior.</p><div style={formGrid}><ReplayQueryField label='candidate_id filter' placeholder='candidate id' value={q.candidateId} onChange={(v) => updateReplayQuery({ candidateId: v })} /><ReplayQueryField label='status filter' placeholder='FILLED or FILLED,REJECTED' value={q.status} onChange={(v) => updateReplayQuery({ status: v })} /><ReplayQueryField label='strategy filter' placeholder='strategy id/family' value={q.strategy} onChange={(v) => updateReplayQuery({ strategy: v })} /><ReplayQueryField label='ts_from_epoch time range filter' placeholder='epoch start' value={q.tsFromEpoch} onChange={(v) => updateReplayQuery({ tsFromEpoch: v })} /><ReplayQueryField label='ts_to_epoch time range filter' placeholder='epoch end' value={q.tsToEpoch} onChange={(v) => updateReplayQuery({ tsToEpoch: v })} /></div><button onClick={() => fetchControlTower(q)}>Apply replay query filters</button><button onClick={resetReplayQuery}>Reset replay query filters</button><ReplayTimelineMetadata query={metadata} /><div style={flagGrid}><Metric label='selected_count' value={outcomeReplay?.selected_count} /><Metric label='blocked_count' value={outcomeReplay?.blocked_count} /><Metric label='filled_count' value={outcomeReplay?.filled_count} /><Metric label='rejected_count' value={outcomeReplay?.rejected_count} /><Metric label='best_quality_score' value={outcomeReplay?.best_quality_score} /></div><div>outcome blockers</div><Chips items={outcomeReplay?.blockers} /><h4>Replay timeline events</h4><Table rows={filteredOutcomeEvents} empty='no outcome replay events yet' /></Card>;
}

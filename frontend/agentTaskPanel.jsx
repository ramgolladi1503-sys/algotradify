import React, { useState } from 'react';
import { Card, Chips, JsonBlock, Metric, Pill, Table, arr, show } from './controlTowerCards.jsx';

const muted = { color: '#99a7c7' };
const flagGrid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 8, margin: '10px 0' };
const subtlePanel = { border: '1px solid #334155', borderRadius: 10, padding: 10, background: '#0b1220', margin: '10px 0' };
const warningPanel = { border: '1px solid #7f1d1d', borderRadius: 10, padding: 10, background: '#3f1d1d', margin: '10px 0', color: '#fecaca' };
const safePanel = { border: '1px solid #14532d', borderRadius: 10, padding: 10, background: '#052e16', margin: '10px 0' };
const reviewButton = { border: 0, borderRadius: 8, padding: '8px 10px', fontWeight: 800, background: '#2563eb', color: 'white', marginRight: 8 };
const rejectButton = { ...reviewButton, background: '#7f1d1d' };
const inputStyle = { border: '1px solid #334155', background: '#0b1220', color: '#e8eefc', borderRadius: 8, padding: 8, marginRight: 8, minWidth: 180 };

export function agentTaskSafeFlagWarnings(payload) {
  const warnings = [];
  if (!payload) return ['agent task payload unavailable'];
  if (payload.read_only !== true) warnings.push('top-level read_only is not true');
  if (payload.is_order_action !== false) warnings.push('top-level is_order_action is not false');
  if (payload.broker_api_called !== false) warnings.push('top-level broker_api_called is not false');
  if (payload.live_mode_touched !== false) warnings.push('top-level live_mode_touched is not false');
  if (payload.allowed_for_live_execution !== false) warnings.push('top-level allowed_for_live_execution is not false');
  arr(payload.records).forEach((record) => {
    if (record?.read_only !== true) warnings.push(`record read_only unsafe: ${show(record?.work_id)}`);
    if (record?.is_order_action !== false) warnings.push(`record is_order_action unsafe: ${show(record?.work_id)}`);
    if (record?.broker_api_called !== false) warnings.push(`record broker_api_called unsafe: ${show(record?.work_id)}`);
    if (record?.live_mode_touched !== false) warnings.push(`record live_mode_touched unsafe: ${show(record?.work_id)}`);
    if (record?.allowed_for_live_execution !== false) warnings.push(`record allowed_for_live_execution unsafe: ${show(record?.work_id)}`);
  });
  return warnings;
}

function AgentTaskSafeFlagPanel({ payload }) {
  const warnings = agentTaskSafeFlagWarnings(payload);
  const style = warnings.length ? warningPanel : safePanel;
  return <div style={style}><strong>Agent task API safety flags</strong><div style={flagGrid}><Metric label='read_only' value={payload?.read_only} danger={payload?.read_only !== true} /><Metric label='is_order_action' value={payload?.is_order_action} danger={payload?.is_order_action !== false} /><Metric label='broker_api_called' value={payload?.broker_api_called} danger={payload?.broker_api_called !== false} /><Metric label='live_mode_touched' value={payload?.live_mode_touched} danger={payload?.live_mode_touched !== false} /><Metric label='allowed_for_live_execution' value={payload?.allowed_for_live_execution} danger={payload?.allowed_for_live_execution !== false} /></div>{warnings.length ? <Chips items={warnings} /> : <div>Agent task query is read-only with broker, order-action, and live-execution flags disabled.</div>}</div>;
}

function agentTaskRows(payload) {
  return arr(payload?.records).map((record) => ({
    work_id: record.work_id,
    source_agent: record.source_agent,
    action: record.action,
    state: record.state,
    risk_level: record.risk_level,
    created_at: record.created_at,
    read_only: record.read_only,
    is_order_action: record.is_order_action,
    broker_api_called: record.broker_api_called,
    live_mode_touched: record.live_mode_touched,
    allowed_for_live_execution: record.allowed_for_live_execution,
  }));
}

function agentTaskStateCounts(records) {
  const counts = {};
  arr(records).forEach((record) => {
    const key = String(record?.state || 'UNKNOWN');
    counts[key] = (counts[key] || 0) + 1;
  });
  return Object.entries(counts).map(([state, count]) => `${state}: ${count}`);
}

export function canRecordPatchDecision(record) {
  return Boolean(record?.work_id && record?.read_only === true && record?.is_order_action === false && record?.broker_api_called === false && record?.live_mode_touched === false && record?.allowed_for_live_execution === false);
}

function PatchReviewControls({ records, onPatchDecision }) {
  const [actor, setActor] = useState('ram');
  const [reason, setReason] = useState('');
  const actionable = arr(records).filter(canRecordPatchDecision);
  if (!onPatchDecision) return <div style={subtlePanel}><strong>Patch-review controls unavailable</strong><div style={muted}>No decision callback is wired. The panel remains display-only.</div></div>;
  return <div style={subtlePanel}><strong>Patch-review decision controls</strong><p style={muted}>These controls only call the patch-review record API. They do not run tasks, apply patches, merge code, place orders, call brokers, or touch live mode.</p><div><input aria-label='patch review actor' value={actor} onChange={(e) => setActor(e.target.value)} style={inputStyle} placeholder='reviewed by' /><input aria-label='patch review reason' value={reason} onChange={(e) => setReason(e.target.value)} style={{ ...inputStyle, minWidth: 260 }} placeholder='optional reason' /></div>{actionable.length ? actionable.map((record) => <div key={record.work_id} style={{ borderTop: '1px solid #334155', paddingTop: 8, marginTop: 8 }}><span style={{ marginRight: 12 }}>{show(record.work_id)} · {show(record.state)} · {show(record.risk_level)}</span><button style={reviewButton} onClick={() => onPatchDecision(record.work_id, 'approval', { approved_by: actor, reason })}>Record Patch Approval</button><button style={rejectButton} onClick={() => onPatchDecision(record.work_id, 'rejection', { rejected_by: actor, reason })}>Record Patch Rejection</button></div>) : <div style={muted}>No safe agent task records available for patch-review recording.</div>}</div>;
}

export function AgentTaskPanel({ agentTasks, patchDecisionResult, onPatchDecision }) {
  const payload = agentTasks || {};
  const status = payload.read_only === true && payload.is_order_action === false && payload.broker_api_called === false && payload.allowed_for_live_execution === false ? 'PATCH_REVIEW_PANEL_SAFE' : 'AGENT_TASK_QUERY_UNAVAILABLE';
  const rows = agentTaskRows(payload);
  return <Card title='Agent Task Patch Review Panel' right={<Pill value={status} />}><p style={muted}>Agent task view from /agent/tasks?limit=20 with patch-review recording controls. The controls only call /agent/tasks/{'{work_id}'}/approval or /agent/tasks/{'{work_id}'}/rejection.</p><AgentTaskSafeFlagPanel payload={payload} /><div style={flagGrid}><Metric label='contract' value={payload.contract} /><Metric label='source_count' value={payload.source_count} /><Metric label='result_count' value={payload.result_count} /><Metric label='record_count' value={rows.length} /></div><div style={subtlePanel}><strong>Agent task state distribution</strong><Chips items={agentTaskStateCounts(payload.records)} /></div><PatchReviewControls records={payload.records} onPatchDecision={onPatchDecision} />{patchDecisionResult ? <div style={patchDecisionResult.ok ? safePanel : warningPanel}><strong>Latest patch-review API result</strong><JsonBlock title='patch review result' value={patchDecisionResult} /></div> : null}<h4>Agent task records</h4><Table rows={rows} empty='no agent task records yet' /><JsonBlock title='agent task query raw payload' value={payload} /></Card>;
}

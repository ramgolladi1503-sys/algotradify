import React from 'react';
import { Card, Chips, JsonBlock, Metric, Pill, Table, arr, show } from './controlTowerCards.jsx';

const muted = { color: '#99a7c7' };
const fieldStyle = { width: '100%', boxSizing: 'border-box', borderRadius: 8, border: '1px solid #334155', background: '#0b1220', color: '#e8eefc', padding: 8 };
const formGrid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 10, margin: '10px 0' };
const flagGrid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 8, margin: '10px 0' };
const subtlePanel = { border: '1px solid #334155', borderRadius: 10, padding: 10, background: '#0b1220', margin: '10px 0' };
const warningPanel = { border: '1px solid #7f1d1d', borderRadius: 10, padding: 10, background: '#3f1d1d', margin: '10px 0', color: '#fecaca' };
const safePanel = { border: '1px solid #14532d', borderRadius: 10, padding: 10, background: '#052e16', margin: '10px 0' };

export const DEFAULT_MOVEMENT_QUERY = { symbol: 'NIFTY', tsEpoch: '77777' };

export function normalizeMovementQuery(raw = {}) {
  return {
    symbol: String(raw.symbol || DEFAULT_MOVEMENT_QUERY.symbol).toUpperCase(),
    tsEpoch: String(raw.tsEpoch ?? raw.ts_epoch ?? raw.ts || DEFAULT_MOVEMENT_QUERY.tsEpoch),
  };
}

export function buildMovementOpportunityQueryString(raw = DEFAULT_MOVEMENT_QUERY) {
  const q = normalizeMovementQuery(raw);
  const params = new URLSearchParams();
  params.set('symbol', q.symbol || DEFAULT_MOVEMENT_QUERY.symbol);
  params.set('ts_epoch', q.tsEpoch || DEFAULT_MOVEMENT_QUERY.tsEpoch);
  return `?${params.toString()}`;
}

function MovementQueryField({ label, value, onChange, placeholder }) {
  return <label><div style={{ ...muted, fontSize: 12 }}>{label}</div><input style={fieldStyle} placeholder={placeholder} value={value || ''} onChange={(e) => onChange(e.target.value)} /></label>;
}

function movementSafeFlagWarnings(payload) {
  const warnings = [];
  if (!payload) return ['movement opportunity payload unavailable'];
  if (payload.read_only !== true) warnings.push('top-level read_only is not true');
  if (payload.is_order_action !== false) warnings.push('top-level is_order_action is not false');
  if (payload.context?.is_order_action !== false) warnings.push('context is_order_action is not false');
  if (payload.summary?.read_only !== true) warnings.push('summary read_only is not true');
  if (payload.summary?.is_order_action !== false) warnings.push('summary is_order_action is not false');
  if (payload.pipeline?.read_only !== true) warnings.push('pipeline read_only is not true');
  if (payload.pipeline?.is_order_action !== false) warnings.push('pipeline is_order_action is not false');
  if (payload.pipeline?.rank_result?.is_order_action !== false) warnings.push('pipeline.rank_result is_order_action is not false');
  arr(payload.ranked_candidates).forEach((candidate) => { if (candidate?.is_order_action !== false) warnings.push(`ranked candidate unsafe flag: ${show(candidate?.candidate_id)}`); });
  arr(payload.rank_records).forEach((record) => { if (record?.is_order_action !== false) warnings.push(`rank record unsafe flag: ${show(record?.candidate_id)}`); });
  arr(payload.exclusions).forEach((exclusion) => { if (exclusion?.is_order_action !== false) warnings.push(`exclusion unsafe flag: ${show(exclusion?.candidate_id)}`); });
  arr(payload.diagnostics).forEach((diagnostic) => { if (diagnostic?.is_order_action !== false) warnings.push(`diagnostic unsafe flag: ${show(diagnostic?.code)}`); });
  return warnings;
}

function MovementSafeFlagPanel({ payload }) {
  const warnings = movementSafeFlagWarnings(payload);
  const style = warnings.length ? warningPanel : safePanel;
  return <div style={style}><strong>Movement API safety flags</strong><div style={flagGrid}><Metric label='read_only' value={payload?.read_only} danger={payload?.read_only !== true} /><Metric label='is_order_action' value={payload?.is_order_action} danger={payload?.is_order_action !== false} /><Metric label='context.is_order_action' value={payload?.context?.is_order_action} danger={payload?.context?.is_order_action !== false} /><Metric label='summary.read_only' value={payload?.summary?.read_only} danger={payload?.summary?.read_only !== true} /><Metric label='summary.is_order_action' value={payload?.summary?.is_order_action} danger={payload?.summary?.is_order_action !== false} /><Metric label='pipeline.read_only' value={payload?.pipeline?.read_only} danger={payload?.pipeline?.read_only !== true} /><Metric label='pipeline.is_order_action' value={payload?.pipeline?.is_order_action} danger={payload?.pipeline?.is_order_action !== false} /><Metric label='pipeline.rank_result.is_order_action' value={payload?.pipeline?.rank_result?.is_order_action} danger={payload?.pipeline?.rank_result?.is_order_action !== false} /></div>{warnings.length ? <Chips items={warnings} /> : <div>Movement opportunity response is read-only and is_order_action=false across the public contract.</div>}</div>;
}

function MovementSummaryPanel({ summary }) {
  return <div style={subtlePanel}><strong>Movement summary</strong><div style={flagGrid}><Metric label='provider_count' value={summary?.provider_count} /><Metric label='registry_candidate_count' value={summary?.registry_candidate_count} /><Metric label='pooled_candidate_count' value={summary?.pooled_candidate_count} /><Metric label='option_enriched_count' value={summary?.option_enriched_count} /><Metric label='allowed_count' value={summary?.allowed_count} /><Metric label='blocked_count' value={summary?.blocked_count} danger={(summary?.blocked_count || 0) > 0} /><Metric label='no_trade_count' value={summary?.no_trade_count} danger={(summary?.no_trade_count || 0) > 0} /><Metric label='ranked_count' value={summary?.ranked_count} /><Metric label='excluded_count' value={summary?.excluded_count} danger={(summary?.excluded_count || 0) > 0} /><Metric label='diagnostic_count' value={summary?.diagnostic_count} danger={(summary?.diagnostic_count || 0) > 0} /><Metric label='warning_count' value={summary?.warning_count} danger={(summary?.warning_count || 0) > 0} /><Metric label='top_candidate_id' value={summary?.top_candidate_id} /></div></div>;
}

function rankedCandidateRows(payload) {
  return arr(payload?.ranked_candidates).map((candidate) => ({
    candidate_id: candidate.candidate_id,
    strategy_id: candidate.strategy_id,
    movement_type: candidate.movement_type,
    direction: candidate.direction,
    status: candidate.status,
    option_confirmation_score: candidate.option_confirmation_score,
    liquidity_score: candidate.liquidity_score,
    freshness_score: candidate.freshness_score,
    is_order_action: candidate.is_order_action,
    blockers: candidate.blockers,
    warnings: candidate.warnings,
  }));
}

function rankRecordRows(payload) {
  return arr(payload?.rank_records).map((record) => ({
    candidate_id: record.candidate_id,
    strategy_id: record.strategy_id,
    rank: record.rank,
    rank_score: record.rank_score,
    is_order_action: record.is_order_action,
  }));
}

function exclusionRows(payload) {
  return arr(payload?.exclusions).map((exclusion) => ({
    candidate_id: exclusion.candidate_id,
    strategy_id: exclusion.strategy_id,
    reason: exclusion.reason,
    status: exclusion.status,
    blockers: exclusion.blockers,
    is_order_action: exclusion.is_order_action,
  }));
}

function diagnosticRows(payload) {
  return arr(payload?.diagnostics).map((diagnostic) => ({
    code: diagnostic.code,
    candidate_id: diagnostic.candidate_id,
    strategy_id: diagnostic.strategy_id,
    message: diagnostic.message,
    is_order_action: diagnostic.is_order_action,
  }));
}

export function MovementOpportunityPanel({ movementOpportunity, movementQuery, updateMovementQuery, applyMovementQuery, resetMovementQuery }) {
  const query = normalizeMovementQuery(movementQuery);
  const payload = movementOpportunity || {};
  const status = payload.read_only === true && payload.is_order_action === false ? 'READ_ONLY_MOVEMENT_OPPORTUNITY' : 'MOVEMENT_OPPORTUNITY_UNAVAILABLE';
  return <Card title='Movement Opportunity Dashboard Read-only Panel' right={<Pill value={status} />}><p style={muted}>Read-only movement opportunity view from /movement-opportunity. This panel consumes the PR 69 API contract and only renders summary, ranked candidates, exclusions, diagnostics, and safe flags.</p><div style={formGrid}><MovementQueryField label='movement symbol query' placeholder='NIFTY' value={query.symbol} onChange={(v) => updateMovementQuery({ symbol: v })} /><MovementQueryField label='movement ts_epoch query' placeholder='77777' value={query.tsEpoch} onChange={(v) => updateMovementQuery({ tsEpoch: v })} /></div><button onClick={() => applyMovementQuery(query)}>Apply movement opportunity query</button><button onClick={resetMovementQuery}>Reset movement opportunity query</button><MovementSafeFlagPanel payload={payload} /><MovementSummaryPanel summary={payload.summary} /><div style={flagGrid}><Metric label='route' value={payload.route} /><Metric label='method' value={payload.method} /><Metric label='api_schema_version' value={payload.api_schema_version} /><Metric label='ranked_candidate_count' value={arr(payload.ranked_candidates).length} /><Metric label='rank_record_count' value={arr(payload.rank_records).length} /><Metric label='exclusion_count' value={arr(payload.exclusions).length} /><Metric label='diagnostic_count' value={arr(payload.diagnostics).length} /></div><div>movement warnings</div><Chips items={payload.warnings} /><h4>Movement ranked candidates</h4><Table rows={rankedCandidateRows(payload)} empty='no movement ranked candidates yet' /><h4>Movement rank records</h4><Table rows={rankRecordRows(payload)} empty='no movement rank records yet' /><h4>Movement exclusions</h4><Table rows={exclusionRows(payload)} empty='no movement exclusions yet' /><h4>Movement diagnostics</h4><Table rows={diagnosticRows(payload)} empty='no movement diagnostics yet' /><JsonBlock title='movement opportunity raw payload' value={payload} /></Card>;
}

# Algotradify Project State

## Latest confirmed merged

GitHub PR #116 / Product PR 97 — Paper Replay Dataset Builder

## Current product PR

PR 98 — Replay Dataset Schema Hardening and Snapshot Contracts

## Current posture

mode=paper_replay_dataset_schema_hardening
live_execution=false
broker_order_placement=false
dashboard_changes=false
strategy_provider_expansion=false
ml_ranker_work=false
agent_scope_expansion=false

## Completed paper truth foundation

- PR 87 — Canonical Paper Event Journal
- PR 88 — Deterministic Paper State Reducer
- PR 89 — Paper Event Ordering and Idempotency Guard
- PR 90 — Paper State Rebuild CLI / Deterministic Rebuild Proof
- PR 91 — Paper State Reconciliation Report
- PR 92 — Paper Trading Pipeline Orchestrator
- PR 93 — Paper Evidence Persistence Layer
- PR 94 — Paper Session Boundary and Reset Controls
- PR 95 — End-to-End Paper Scenario Suite
- PR 96 — Paper Evidence Export Bundle
- PR 97 — Paper Replay Dataset Builder

## Completed agent mini-scope

- Agent PR 1 — Agent Work Request Contract
- Agent PR 2 — Agent Scope Guard
- Agent PR 3 — Agent Approval and Evidence Journal
- Agent PR 4 — Local Agent Work CLI
- Agent PR 5 — Agent Task Store
- Agent PR 6 — POST /agent/tasks Intake Webhook
- Agent PR 7 — Agent Task Query API
- Agent PR 8 — Read-only Dashboard Agent Panel
- Agent PR 9 — Patch-only Approval API
- Agent PR 10 — Dashboard Patch Approval Controls

## Current implementation focus

- Lock the paper replay dataset schema contract with an exact v1 snapshot.
- Prove required replay row keys cannot drift silently.
- Prove required replay result keys cannot drift silently.
- Prove safe flags and scope boundaries cannot drift silently.
- Prove unsafe replay rows, unknown schema versions, invalid row types, and analysis/profitability leakage are rejected.
- Keep replay dataset schema hardening disconnected from runtime/live/API/UI/broker/agent-system work.

## Next product PR only after PR 98 merges

PR 99 — Replay Dataset Validation CLI

## Hard rules

- No live execution before PR 115.
- No dashboard before PR 113.
- No new strategy providers before PR 100.
- No ML ranker before expectancy is proven.
- No broker adapter work in this wave.
- Journal is truth.
- Reducer derives state.
- Reconciliation reports drift; it does not become truth.
- Pipeline orchestrates existing paper modules; it does not become runtime/live execution.
- Persistence stores evidence only; it does not become runtime execution.
- Session reset markers are non-destructive evidence boundaries only.
- Scenario suite proves controlled paper paths only; it is not runtime execution.
- Export bundle packages evidence only; it does not generate replay datasets or profitability proof.
- Replay dataset builder shapes source-traceable rows only; it does not compute labels, rewards, expectancy, profitability, or ML features.
- Replay dataset schema hardening locks the v1 contract only; it does not add runtime wiring, API/UI, broker/live execution, strategy work, or agent-system work.
- Agent mini-scope is complete. Do not add more agent PRs unless a real blocker exists.
- Every PR must include Grill, GSD, and Hermes handoff artifacts.
- Every PR must include acceptance proof.

## Process note

Agent workflow discipline is process-level only. It must not change runtime trading behavior.

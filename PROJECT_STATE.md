# Algotradify Project State

## Latest confirmed merged

GitHub PR #135 — Agent PR 14 — PR Handoff Evidence Validator: MERGED

## Current locked implementation wave

Agent Governance + Role-Based Mini-Agent Enforcement Wave

Current PR:

```text
Agent PR 15 — CI Agent Architecture Gate
```

## Current posture

```text
mode=agent_governance_pr15_ci_architecture_gate
runtime_correction_wave=complete
agent_governance_wave=active
current_agent_governance_pr=15
next_allowed_work=Agent PR 15 only
live_execution=guarded_explicit_only
broker_order_placement=false
dashboard_changes=false
strategy_provider_expansion=false
ml_ranker_work=false
runtime_behavior_changes=none
role_registry=complete
workflow_state_machine=complete
handoff_artifact_contract=complete
handoff_validator=complete
ci_architecture_gate=true
changed_file_auditor=false
architecture_audit_report=false
```

## Locked Agent Governance PR 11–18 order

```text
PR 11 — Agent Role Registry Contract: DONE
PR 12 — Role-Based Workflow State Machine: DONE
PR 13 — Role Handoff Artifact Contract: DONE
PR 14 — PR Handoff Evidence Validator: DONE
PR 15 — CI Agent Architecture Gate: IN PROGRESS
PR 16 — Changed-File Scope Auditor: LOCKED NEXT
PR 17 — PR Template and Local Developer Gate: LOCKED
PR 18 — Architecture Replay / Audit Report: LOCKED
```

No deviation until PR 18 is complete.

## Agent PR 15 boundary

PR 15 adds the CI architecture gate only.

It may add/change:

- `agent_system/architecture_gate.py`
- `agent_system/__init__.py` exports for architecture gate
- `scripts/run_agent_architecture_gate.py`
- `tests/test_agent_architecture_gate.py`
- `.github/workflows/agent-architecture-ci.yml`
- `docs/agent-architecture-ci-gate.md`
- Agent PR 15 role handoff artifacts
- project-state metadata

It must not add/change:

- changed-file auditor
- PR template gate
- architecture audit report
- API routes
- frontend/dashboard behavior
- broker/order behavior
- live config behavior
- runtime behavior
- strategy/ranker/profitability work

## Why normal product work is paused

Normal product work remains paused while the role-based mini-agent architecture is made enforceable.

The immediate goal is not to add trading features. The immediate goal is to stop future PRs from depending on manual memory and make the role-based architecture enforceable in code and CI.

## Runtime correction wave

- Runtime Correction PR 1 — Runtime Ownership Audit: DONE
- Runtime Correction PR 2 — Tradebot Source Import Manifest and Collision Report: DONE
- Runtime Correction PR 3 — Native Runtime Source Import: DONE
- Runtime Correction PR 4 — Native Runtime Contract and Preflight Hardening: DONE
- Runtime Correction PR 5 — Root Native main.py Promotion: DONE
- Runtime Correction PR 6 — Native run_live / Operator Boot Commands: DONE
- Runtime Correction PR 7 — API and Control Tower Runtime Ownership Wiring: DONE
- Runtime Correction PR 8 — Broker Auth Visibility and Startup UX: DONE
- Runtime Correction PR 9 — Compatibility Cleanup and External Runtime Deprecation: DONE
- Runtime Correction PR 10 — Full Regression Gate and Migration Lock: DONE

## Runtime correction discipline

- Do not reopen runtime correction work unless the migration lock catches a real regression.
- Do not silently fall back to external Tradebot once native ownership is required.
- Do not import secrets, tokens, logs, databases, `.env`, or runtime artifacts.
- Do not weaken existing paper/replay/agent/safety contracts.
- Do not add broker order controls or make LIVE the default.

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

## Active role-based governance wave

- Agent PR 11 — Agent Role Registry Contract: DONE
- Agent PR 12 — Role-Based Workflow State Machine: DONE
- Agent PR 13 — Role Handoff Artifact Contract: DONE
- Agent PR 14 — PR Handoff Evidence Validator: DONE
- Agent PR 15 — CI Agent Architecture Gate: IN PROGRESS
- Agent PR 16 — Changed-File Scope Auditor: LOCKED NEXT
- Agent PR 17 — PR Template and Local Developer Gate: LOCKED
- Agent PR 18 — Architecture Replay / Audit Report: LOCKED

## Paused product work

- PR 98 — Replay Dataset Schema Hardening and Snapshot Contracts: PAUSED until Agent Governance PR 11–18 completes or an explicit approved exception is documented.
- PR 99 — Replay Dataset Validation CLI: PAUSED.

## Hard rules

- No live execution before the approved runtime/live safety gate.
- No broker adapter work during the role-based governance wave.
- No new strategy providers during the role-based governance wave.
- No ML ranker during the role-based governance wave.
- No product dashboard expansion during the role-based governance wave.
- No auto-merge during the role-based governance wave.
- No mobile approval screen during the role-based governance wave.
- No agent worker during the role-based governance wave.
- No runtime execution behavior during the role-based governance wave.
- Journal is truth.
- Reducer derives state.
- Reconciliation reports drift; it does not become truth.
- Pipeline orchestrates existing paper modules; it does not become runtime/live execution.
- Persistence stores evidence only; it does not become runtime execution.
- Session reset markers are non-destructive evidence boundaries only.
- Scenario suite proves controlled paper paths only; it is not runtime execution.
- Export bundle packages evidence only; it does not generate replay datasets or profitability proof.
- Replay dataset builder shapes source-traceable rows only; it does not compute labels, rewards, expectancy, profitability, or ML features.
- Every Agent Governance PR must pass through Grill, GSD, Hermes, and acceptance proof.

## Process note

Proceed only with Agent PR 15 until it is merged. After PR 15 merges, proceed only to PR 16. Do not skip or reorder PR 11–18.

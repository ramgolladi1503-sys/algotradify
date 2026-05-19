# Algotradify Project State

## Latest confirmed merged

GitHub PR #127 — Runtime Correction PR 9 — Compatibility Cleanup and External Runtime Deprecation: MERGED

## Current correction PR

Runtime Correction PR 10 — Full Regression Gate and Migration Lock

## Current posture

mode=runtime_migration_lock_final_gate
live_execution=guarded_explicit_only
broker_order_placement=false
dashboard_changes=false
strategy_provider_expansion=false
ml_ranker_work=false
agent_scope_expansion=false
runtime_behavior_changes=none_lock_only
source_import=true
import_planning_only=false
root_main_promotion=true
root_run_live_promotion=guarded_live_entrypoint
external_runtime_fallback=deprecated_explicit_opt_in_only
migration_lock=active

## Why normal product work is paused

Normal Product PR 98 work is paused until runtime ownership correction is locked.

The current correction wave exists because algotradify had built valuable product layers around API, Control Tower, paper trading, replay evidence, dry-run safety, and agent workflow, but the runtime ownership boundary was not strict enough.

The immediate goal is not to add features. The immediate goal is to lock the corrected native-runtime posture so future product work cannot silently drift back into wrapper/external-runtime ambiguity.

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
- Runtime Correction PR 10 — Full Regression Gate and Migration Lock: IN PROGRESS

## Runtime Correction PR 2 boundary

PR 2 is planning-only.

It may add:

- a read-only import planning script
- import planning tests
- runtime source manifest schema
- import planning documentation
- Grill, GSD, and Hermes handoff artifacts
- project-state metadata

It must not:

- copy Tradebot source
- replace `main.py`
- change `runtime_contract.py`
- change runtime behavior
- change API/frontend/paper/agent behavior
- call broker APIs
- add auth behavior
- add UI controls

## Runtime Correction PR 3 boundary

PR 3 imports native Tradebot runtime source as tracked source without wiring runtime behavior.

It may add:

- core/
- config/
- dashboard/
- ml/
- models/
- rl/
- fixtures/
- strategies/ missing files only
- runtime_native/tradebot_main.py
- runtime_native/tradebot_run_live.sh
- runtime_native/tradebot_requirements.txt
- RUNTIME_SOURCE_MANIFEST.json
- native source import tests
- native source import documentation
- Grill, GSD, and Hermes handoff artifacts
- project-state metadata

It must not:

- replace root `main.py`
- promote root `run_live.sh`
- change `runtime_contract.py`
- change API/frontend/paper/agent behavior
- call broker APIs
- add auth behavior
- add UI controls
- make LIVE the default

## Runtime Correction PR 4 boundary

PR 4 hardens native runtime contract and preflight visibility only.

It may add/change:

- `runtime_contract.py` native source detection
- strict native preflight mode with `ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true`
- external fallback opt-out with `ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=false`
- preflight output fields for runtime ownership, native source presence, native main promotion, external runtime allowed/used
- native runtime contract tests
- documentation and Grill/GSD/Hermes handoff artifacts
- project-state metadata

It must not:

- replace root `main.py`
- promote root `run_live.sh`
- change API/frontend/paper/agent behavior
- call broker APIs
- add auth behavior
- add UI controls
- make LIVE the default
- remove wrapper boot behavior before Runtime Correction PR 5

## Runtime Correction PR 5 boundary

PR 5 promotes root `main.py` to the native runtime entrypoint.

It may add/change:

- root `main.py` promoted from imported native Tradebot startup flow
- `runtime_contract.py` default native root selection after promotion
- tests proving dynamic external loading is removed
- tests proving safety-critical startup calls remain present
- tests proving root `run_live.sh` is still not promoted
- native main documentation
- Grill, GSD, and Hermes handoff artifacts
- project-state metadata

It must not:

- promote root `run_live.sh`
- change API/frontend/paper/agent behavior
- add dashboard controls
- add broker order behavior
- add auth endpoints
- make LIVE the default
- remove safety-critical startup checks from native main

## Runtime Correction PR 6 boundary

PR 6 adds native operator boot commands.

It may add/change:

- guarded root `run_live.sh`
- safe operator boot CLI for preflight, SIM, PAPER, and API-only startup
- operator command documentation
- tests proving live startup requires explicit confirmation
- tests proving SIM/PAPER/UI commands do not force LIVE
- Grill, GSD, and Hermes handoff artifacts
- project-state metadata

It must not:

- add broker order behavior
- add auth API endpoints
- add dashboard controls
- change frontend behavior
- change paper/agent internals
- make LIVE the default
- allow `./run_live.sh` to start live without explicit confirmation

## Runtime Correction PR 7 boundary

PR 7 wires runtime ownership visibility into API and Control Tower.

It may add/change:

- read-only runtime ownership payload builder
- GET-only `/runtime/ownership` API route
- response schema for runtime ownership status
- read-only Control Tower panel helper/normalizer
- tests proving safe flags and no action affordances
- runtime ownership documentation
- Grill, GSD, and Hermes handoff artifacts
- project-state metadata

It must not:

- add broker order behavior
- add auth API endpoints
- add dashboard action controls
- change frontend execution behavior
- change paper/agent internals
- make LIVE the default
- mutate runtime state
- start runtime workers

## Runtime Correction PR 8 boundary

PR 8 adds broker auth visibility and startup UX only.

It may add/change:

- local-only sanitized broker auth visibility payload
- GET-only `/broker/auth/visibility` API route
- response schema for auth visibility
- read-only Control Tower auth visibility panel helper/normalizer
- startup command guidance for login-only, validate-only, SIM, PAPER, and API-only startup
- tests proving no raw token/secret exposure and no broker/profile probes
- auth visibility documentation
- Grill, GSD, and Hermes handoff artifacts
- project-state metadata

It must not:

- call broker APIs
- run login from API or dashboard
- mutate tokens
- expose raw tokens or API secrets
- add auth mutation endpoints
- add broker order behavior
- add dashboard action controls
- change paper/agent internals
- make LIVE the default
- start runtime workers

## Runtime Correction PR 9 boundary

PR 9 deprecates external runtime compatibility and disables silent fallback by default.

It may add/change:

- `runtime_contract.py` default external fallback behavior
- explicit temporary opt-in with `ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=true`
- preflight deprecation metadata for external fallback
- runtime ownership API deprecation fields
- tests proving native default and external opt-in behavior
- external fallback deprecation documentation
- Grill, GSD, and Hermes handoff artifacts
- project-state metadata

It must not:

- change root `main.py`
- change root `run_live.sh`
- change operator boot commands
- add broker/auth/order behavior
- change dashboard controls
- change paper/agent internals
- remove explicit external opt-in before PR 10
- make LIVE the default

## Runtime Correction PR 10 boundary

PR 10 locks the completed correction wave with a deterministic regression gate.

It may add/change:

- read-only runtime migration lock checker
- migration lock tests with injected regression cases
- migration lock documentation
- Grill, GSD, and Hermes handoff artifacts
- project-state metadata

It must not:

- change root `main.py` behavior
- change root `run_live.sh` behavior
- change operator boot behavior
- change runtime contract behavior
- add broker/auth/order behavior
- add dashboard action controls
- change paper/agent internals
- make LIVE the default
- add new product features

## Runtime correction discipline

- Do not expand beyond the 10 correction PRs unless a real blocker is discovered.
- Do not add unrelated product features during this wave.
- Do not rewrite Tradebot main from scratch.
- Do not silently fall back to external Tradebot once native ownership is required.
- Do not import secrets, tokens, logs, databases, `.env`, or runtime artifacts.
- Do not weaken existing paper/replay/agent/safety contracts.
- Do not add broker order controls or make LIVE the default.

## Mini-agent process gate

The completed mini-agent architecture is used as a process gate for every correction PR.

Each correction PR must include:

- Grill handoff artifact — challenges scope, rejects drift, and defines hard rejection conditions.
- GSD handoff artifact — defines the minimal execution plan and exact files allowed.
- Hermes handoff artifact — reviews final diff boundaries and confirms the PR did not expand.
- Acceptance proof — commands/tests/evidence proving the PR did exactly what it claimed.

Important boundary:

Agent workflow discipline is process-level only. It must not add new agent features, runtime workers, auto-merge behavior, mobile approvals, broker actions, paper orders, live config mutation, or execution behavior during this correction wave.

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

## Paused product work

- PR 98 — Replay Dataset Schema Hardening and Snapshot Contracts: PAUSED until runtime correction wave completes or explicitly resumes.
- PR 99 — Replay Dataset Validation CLI: PAUSED.

## Hard rules

- No live execution before the approved runtime/live safety gate.
- No broker adapter work during this correction wave except read-only auth visibility in Runtime Correction PR 8.
- No new strategy providers during this correction wave.
- No ML ranker during this correction wave.
- No agent scope expansion during this correction wave.
- Journal is truth.
- Reducer derives state.
- Reconciliation reports drift; it does not become truth.
- Pipeline orchestrates existing paper modules; it does not become runtime/live execution.
- Persistence stores evidence only; it does not become runtime execution.
- Session reset markers are non-destructive evidence boundaries only.
- Scenario suite proves controlled paper paths only; it is not runtime execution.
- Export bundle packages evidence only; it does not generate replay datasets or profitability proof.
- Replay dataset builder shapes source-traceable rows only; it does not compute labels, rewards, expectancy, profitability, or ML features.
- Agent mini-scope is complete. Do not add more agent PRs unless a real blocker exists.
- Every correction PR must pass through Grill, GSD, Hermes, and acceptance proof.

## Process note

Runtime Correction PR 10 locks runtime ownership. After it merges, resume normal product roadmap deliberately; do not reopen correction work unless the lock catches a real regression.

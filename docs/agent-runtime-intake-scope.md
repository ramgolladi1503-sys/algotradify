# Agent Runtime Intake Scope

Status: scope bible / build plan
Project: algotradify
Created: 2026-05-18

This document defines the safe path for adding agent intake capability to algotradify without corrupting the paper-truth foundation, broker safety boundaries, or live-readiness roadmap.

The purpose is not to let agents trade. The purpose is to let external or local agents submit auditable work requests that are normalized, guarded, approved, and recorded before any code, UI, paper, or live-adjacent behavior can happen.

## Hard truth

Do not jump from PR stage-gate documents directly to mobile approval, dashboard controls, auto-merge, paper orders, or live configuration.

The missing middle layer is a real runtime-safe agent intake system:

```text
Agent work request
  -> normalize contract
  -> scope guard
  -> approval decision
  -> evidence journal
  -> optional read-only API/query surface
  -> optional review UI
```

Until that exists, any dashboard or mobile screen is only theater.

## Existing algotradify state

Already present:

- `AGENTS.md` repo operating contract.
- Grill / GSD / Hermes stage discipline.
- PR body stage-gate checker.
- Handoff artifact protocol.
- Paper-truth foundation safety posture.

Not yet present:

- Agent work request domain model.
- Agent scope guard.
- Agent approval engine.
- Agent evidence journal.
- Agent task persistence/query API.
- `/agent/tasks` webhook.
- Mobile approval workflow.
- Dashboard agent panel.
- Any safe bridge from agent request to paper order proposal.
- Any safe bridge from agent request to live configuration.

## Non-negotiable safety rules

Every agent-related PR must preserve these defaults unless the PR explicitly scopes and proves otherwise:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
real_order_id=null
```

Agents must not:

- place orders
- modify orders
- cancel orders
- call broker APIs
- touch credentials
- enable live mode
- change live config
- bypass risk gates
- bypass quote/feed freshness gates
- bypass kill switches
- auto-merge trading code
- silently retry unsafe requests into success
- hide broken input with fallback defaults

## Immediate implementation wave

This wave is safe to build now. It is local/runtime foundation only. No webhook, no dashboard, no mobile, no paper order triggering, no live config.

### Agent PR 1 — Agent Work Contract Foundation

Goal: define the canonical input/output contract for all agent work requests.

Files to change:

```text
agent_system/__init__.py
agent_system/work_contract.py
tests/test_agent_work_contract.py
docs/agent-work-contract.md
```

Core objects:

```text
AgentSource
AgentAction
AgentRiskLevel
AgentWorkRequest
AgentWorkDecision
normalize_agent_work_request
build_agent_work_id
agent_work_schema_contract
```

Required behavior:

- Normalize source agent names.
- Normalize action names.
- Preserve requested paths, allowed paths, forbidden paths.
- Require title and scope.
- Create deterministic work IDs.
- Keep schema version explicit.
- Treat missing fields as invalid or blocked, not guessed.

Negative tests:

- missing source agent
- unknown source agent
- missing action
- empty title
- empty scope
- missing requested paths
- non-list path fields
- unstable work ID generation
- unsafe action appears in allowed action set

Acceptance proof:

```bash
python -m pytest tests/test_agent_work_contract.py -q
```

Do not touch:

```text
api/
frontend/
dashboard/
paper_trading/
broker_contract/
execution_safety/
execution_readiness/
strategies/
movement_engine/
top_selector/
main.py
runtime wiring
```

### Agent PR 2 — Agent Scope Guard

Goal: block dangerous agent requests before approval or execution can exist.

Files to change:

```text
agent_system/scope_guard.py
tests/test_agent_scope_guard.py
docs/agent-scope-guard.md
```

Core behavior:

- Allow Grill only to review/critique/audit.
- Allow Hermes only to design/contracts/workflow/docs.
- Allow GSD only to plan/tests/patch/docs/fix scoped failures.
- Block all order actions.
- Block broker, live, config, credentials, secrets, and kill-switch paths.
- Mark core risk/execution/broker areas as high risk requiring human approval.
- Auto-approve only docs/tests-only patch scope.
- Fail closed on unclear paths.

Forbidden actions:

```text
PLACE_ORDER
MODIFY_ORDER
CANCEL_ORDER
EXIT_POSITION
ENABLE_LIVE
DISABLE_RISK_GATE
CHANGE_BROKER_CONFIG
CHANGE_LIVE_CONFIG
CALL_BROKER_API
```

Forbidden path prefixes:

```text
.env
credentials.py
config/secrets
runtime/live
logs/broker
broker_contract/
execution_safety/live
execution_readiness/live
paper_broker/live
```

High-risk path prefixes:

```text
broker_contract/
execution_safety/
execution_readiness/
paper_trading/
core/risk
core/execution
config/
main.py
run_live.sh
```

Negative tests:

- Grill cannot generate patch.
- Hermes cannot touch broker/runtime/live paths.
- GSD cannot place order.
- Any source cannot enable live mode.
- Forbidden path blocks.
- Outside allowed path blocks.
- High-risk path requires human approval.
- Docs/tests-only scope can be approved for patch.
- Empty requested paths block.

Acceptance proof:

```bash
python -m pytest tests/test_agent_scope_guard.py -q
```

Do not touch:

```text
api/
frontend/
dashboard/
paper_trading runtime behavior
broker/live execution
strategy/provider/ranker code
```

### Agent PR 3 — Agent Approval and Evidence Journal

Goal: convert a scope decision into an approval decision and write immutable local evidence.

Files to change:

```text
agent_system/approval.py
agent_system/evidence.py
tests/test_agent_approval.py
tests/test_agent_evidence.py
docs/agent-approval-evidence.md
```

Approval rules:

- Block if scope decision is blocked.
- Block if human approval is required but missing.
- Never approve order actions.
- Never approve broker API calls.
- Never approve live config changes.
- Approve only patch/documentation/test work.
- Always return explicit blockers and reasons.

Evidence rules:

- Write latest evidence to `runtime/agent_work/agent_work_latest.json`.
- Append daily JSONL evidence to `runtime/agent_work/agent_work_YYYY-MM-DD.jsonl`.
- Write request, scope decision, approval decision, schema version, timestamp, and safety flags.
- Use atomic latest-file replacement.
- Do not write secrets.
- Do not hide evidence write failure.

Negative tests:

- blocked scope cannot be approved
- human approval required but missing blocks
- order action approval blocks
- broker flag approval blocks
- live flag approval blocks
- approved patch still has `allowed_for_live_execution=false`
- evidence write includes safe flags
- evidence write blocks unsafe payload
- latest evidence and JSONL append are deterministic enough for tests

Acceptance proof:

```bash
python -m pytest tests/test_agent_approval.py tests/test_agent_evidence.py -q
```

Do not touch:

```text
api/
frontend/
dashboard/
broker/live execution
paper order pipeline
main.py
```

### Agent PR 4 — Local Agent Work CLI

Goal: allow safe local submission of agent work payloads before any webhook exists.

Files to change:

```text
scripts/submit_agent_work.py
docs/samples/grill-agent-work.json
docs/samples/hermes-agent-work.json
docs/samples/gsd-agent-work.json
tests/test_submit_agent_work.py
docs/local-agent-work-cli.md
```

CLI behavior:

```bash
PYTHONPATH=. python scripts/submit_agent_work.py --payload docs/samples/gsd-agent-work.json
```

Supported flags:

```text
--payload
--approve
--approved-by
--evidence-root
--json
```

Exit codes:

```text
0 = approved or safely accepted according to state
1 = rejected approval
2 = blocked scope/input
3 = evidence write failure
```

Negative tests:

- missing payload file exits non-zero
- malformed JSON exits non-zero
- blocked request exits 2
- rejected approval exits 1
- approved docs/tests request exits 0
- high-risk request without approval exits 1
- high-risk request with approval exits 0 but runtime/live remains false
- CLI output contains no order controls

Acceptance proof:

```bash
python -m pytest tests/test_submit_agent_work.py -q
PYTHONPATH=. python scripts/submit_agent_work.py --payload docs/samples/gsd-agent-work.json --json
```

Do not touch:

```text
api/
frontend/
dashboard/
paper_trading runtime behavior
broker/live execution
strategy/provider/ranker code
```

## What can start after Agent PR 1-4?

After Agent PR 1-4 are implemented and merged, only these can start:

```text
POST /agent/tasks webhook: YES, intake-only
Dashboard agent panel: YES, read-only first
Mobile approval screen: YES, approval UI only after backend approval API exists
Agent-triggered paper order proposal: LATER, proposal-only after more gates
```

These must not start immediately after Agent PR 1-4:

```text
Agent auto-merge: NO
Agent-created broker action: NO
Agent-triggered live config: NO
Direct agent-triggered paper orders: NO
```

## Second implementation wave: safe intake API and read-only UI

This wave can start only after Agent PR 1-4 are merged.

### Agent PR 5 — Agent Task Store

Goal: store agent task evidence in queryable local records without execution.

Files to change:

```text
agent_system/task_store.py
tests/test_agent_task_store.py
docs/agent-task-store.md
```

Behavior:

- Persist each submitted task as immutable JSON under `runtime/agent_work/tasks/`.
- Maintain a read-only index file.
- Support query by work_id, source_agent, action, state, risk_level, created_at range.
- Return read-only task summaries.
- Fail closed on corrupt task files.

Negative tests:

- corrupt task file blocks index load
- missing task ID returns not found
- duplicate work ID is deterministic no-op only if payload is identical
- conflicting duplicate work ID blocks
- index cannot mark task as executed
- task store output has no broker/live/order flags set true

Acceptance proof:

```bash
python -m pytest tests/test_agent_task_store.py -q
```

### Agent PR 6 — `POST /agent/tasks` Intake Webhook

Goal: accept agent work requests over API and return scope/approval/evidence result.

Allowed now: yes, intake-only.

Files to change:

```text
api/agent_tasks.py
api/main.py or existing API router registration file
tests/test_agent_tasks_api.py
docs/agent-tasks-webhook.md
```

Endpoint:

```text
POST /agent/tasks
```

Request body:

```text
AgentWorkRequest JSON
```

Response body:

```text
work_id
accepted
state
risk_level
allowed_for_patch
requires_human_approval
read_only
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
blockers
warnings
reasons
evidence_ref
```

Strict limitations:

- No code execution.
- No patch application.
- No GitHub merge.
- No broker call.
- No paper order call.
- No live config mutation.
- No dashboard action.
- No background worker.

Negative tests:

- forbidden action returns blocked
- unknown source returns blocked
- forbidden path returns blocked
- high-risk path returns waiting approval
- docs/tests-only request returns approved for patch
- response contains no order controls
- broker flags always false
- live flags always false
- malformed JSON returns validation failure
- evidence is written for valid request

Acceptance proof:

```bash
python -m pytest tests/test_agent_tasks_api.py -q
```

### Agent PR 7 — Agent Task Query API

Goal: expose read-only task lookup for UI/mobile.

Endpoints:

```text
GET /agent/tasks
GET /agent/tasks/{work_id}
```

Files to change:

```text
api/agent_tasks.py
tests/test_agent_tasks_query_api.py
docs/agent-task-query-api.md
```

Query filters:

```text
source_agent
action
state
risk_level
created_from
created_to
limit
```

Strict limitations:

- No approve endpoint yet.
- No mutate endpoint.
- No execute endpoint.
- No broker/live/paper action.

Negative tests:

- list is read-only
- details are read-only
- missing work ID returns safe not found
- corrupt store blocks safely
- query cannot include action verbs like submit/cancel/merge/order

Acceptance proof:

```bash
python -m pytest tests/test_agent_tasks_query_api.py -q
```

### Agent PR 8 — Read-only Dashboard Agent Panel

Goal: display submitted agent tasks and their safety decisions.

Allowed now: yes, read-only only.

Files to change:

```text
frontend or dashboard agent panel files, depending on current app structure
tests for dashboard/panel rendering if available
docs/dashboard-agent-panel.md
```

Panel must show:

```text
work_id
source_agent
action
title
state
risk_level
allowed_for_patch
requires_human_approval
blockers
warnings
reasons
evidence_ref
safe flags
```

Strict limitations:

- No approve button.
- No reject button.
- No merge button.
- No apply patch button.
- No run agent button.
- No order button.
- No broker action.
- No live config control.

Negative tests:

- no submit/modify/cancel/order/live/merge controls appear
- blocked tasks render blockers
- high-risk tasks render human approval required
- safe flags are visible
- missing/corrupt API response renders safe error, not fake success

Acceptance proof:

```bash
python -m pytest <dashboard tests> -q
```

If the dashboard stack lacks reliable UI tests, add a pure rendering helper test before touching broad UI.

### Agent PR 9 — Approval API for Patch-only Work

Goal: allow explicit human approval for patch-only agent work.

Allowed now: yes, but only for patch/workflow approval.

Endpoints:

```text
POST /agent/tasks/{work_id}/approve
POST /agent/tasks/{work_id}/reject
```

Files to change:

```text
api/agent_task_approval.py
agent_system/task_store.py
tests/test_agent_task_approval_api.py
docs/agent-task-approval-api.md
```

Approval scope:

```text
allowed_for_patch=true
allowed_for_runtime_wiring=false
allowed_for_order_action=false
allowed_for_broker_api=false
allowed_for_live_execution=false
```

Negative tests:

- blocked work cannot be approved
- order action cannot be approved
- broker action cannot be approved
- live config cannot be approved
- high-risk code requires explicit approved_by
- approval writes evidence
- reject writes evidence
- approval cannot mutate source request

Acceptance proof:

```bash
python -m pytest tests/test_agent_task_approval_api.py -q
```

### Agent PR 10 — Mobile Approval Screen

Goal: mobile-friendly approval/rejection UI for patch-only work.

Allowed now: yes, after Agent PR 9 only.

Screen must show:

```text
work_id
source_agent
action
scope
requested_paths
risk_level
blockers
warnings
reasons
approval state
safe flags
```

Allowed actions:

```text
approve patch-only work
reject work
add review note
```

Forbidden actions:

```text
approve order action
approve broker action
approve live config
run patch
merge PR
trigger paper order
trigger live order
```

Negative tests:

- mobile screen cannot approve blocked work
- mobile screen cannot approve broker/live/order requests
- mobile screen cannot hide blockers
- mobile approval requires visible safe flags
- mobile rejection writes audit note

Acceptance proof:

```bash
python -m pytest <mobile approval tests> -q
```

## Third implementation wave: dangerous features and the real answer

### POST `/agent/tasks` webhook

Decision: yes, after Agent PR 1-5.

Allowed version:

```text
intake-only
validation-only
evidence-writing
no execution
```

Forbidden version:

```text
agent sends task -> system changes code/trading state automatically
```

### Mobile approval screen

Decision: yes, after approval API exists.

Allowed version:

```text
patch-only human approval UI
reject/approve/note only
```

Forbidden version:

```text
approve broker order
approve live config
approve auto-merge
```

### Dashboard agent panel

Decision: yes, read-only first.

Allowed version:

```text
visibility panel for task decisions/evidence
```

Forbidden version:

```text
control center that runs agents or trading actions
```

### Agent auto-merge

Decision: no for trading/product code.

Possible future narrow exception:

```text
docs-only auto-merge candidate
only after CI passes
only with branch protection
only with explicit human label
only if changed files are restricted to docs/samples
```

Even then, call it `auto-merge candidate`, not true auto-merge.

Minimum future gates before considering docs-only auto-merge:

- branch protection enabled
- required CI checks enabled
- changed-files allowlist guard
- no product/runtime/test files touched
- explicit owner approval label
- audit evidence written

### Agent-created broker action

Decision: no in this roadmap wave.

Allowed future version:

```text
agent-created broker action proposal only
human-approved
risk-gated
kill-switch-gated
not executed by agent
```

Forbidden version:

```text
agent creates real broker order/action directly
```

This must wait until live-readiness gates are already proven.

### Agent-triggered paper orders

Decision: not direct after Agent PR 1-4. Possible later as proposal-only.

Allowed future version:

```text
agent submits PAPER_ORDER_PROPOSAL
paper proposal enters scope guard
human approval or deterministic policy approval required
paper pipeline consumes only approved proposal
journal records every transition
```

Forbidden version:

```text
agent directly calls paper order pipeline without approval/evidence
```

Minimum future PRs before paper order proposal:

1. Agent paper proposal contract.
2. Paper proposal scope guard.
3. Paper proposal approval evidence.
4. Paper proposal to canonical event bridge.
5. Paper pipeline consumption test.
6. Replay proof that agent-origin paper orders remain paper-only.

### Agent-triggered live config

Decision: no.

Allowed future version:

```text
agent suggests live config diff
human reviews diff
system validates against live-readiness policy
config remains inactive until separate live gate approves
```

Forbidden version:

```text
agent directly changes live config
agent enables live mode
agent edits credentials/secrets
agent bypasses live readiness
```

This should not be built until live-readiness PRs exist and paper expectancy is proven.

## Correct build order

Use this exact order unless a future scope review rejects it:

```text
Scope PR — this document
Agent PR 1 — Agent Work Contract Foundation
Agent PR 2 — Agent Scope Guard
Agent PR 3 — Agent Approval and Evidence Journal
Agent PR 4 — Local Agent Work CLI
Agent PR 5 — Agent Task Store
Agent PR 6 — POST /agent/tasks Intake Webhook
Agent PR 7 — Agent Task Query API
Agent PR 8 — Read-only Dashboard Agent Panel
Agent PR 9 — Patch-only Approval API
Agent PR 10 — Mobile Approval Screen
```

Stop there.

Do not continue to auto-merge, broker action, paper order triggering, or live config until a new scope review proves the system is ready.

## Resume point after this wave

After Agent PR 1-10 are implemented and merged, resume the paused paper-truth roadmap from the last unfinished paper PR.

Before resuming, update project state with:

```text
Agent runtime intake foundation: complete
Last merged agent PR: <number>
Webhook: intake-only
Dashboard: read-only
Mobile approval: patch-only
Auto-merge: blocked
Broker action: blocked
Paper order trigger: blocked unless proposal-only scope is opened later
Live config: blocked
```

## Merge blockers for this scope

Reject any PR in this agent wave if it:

- places or modifies orders
- calls broker APIs
- touches credentials or secrets
- enables live mode
- changes live config
- adds dashboard controls outside scoped read-only/approval UI
- auto-merges code
- directly triggers paper order execution
- weakens existing paper-truth tests
- hides unsafe input behind fallback
- mixes paper-truth implementation with agent UI/API work
- changes unrelated strategy, ranking, execution, or broker code

## Brutal rule

If an agent can mutate trading state before the task is normalized, guarded, approved, and evidenced, the design is wrong.

If a UI button exists before the backend can prove safety, the UI is fake progress.

If auto-merge touches trading code, it is not automation. It is negligence.

# Agent Tasks Intake Webhook

Status: Agent PR 6
Scope: `POST /agent/tasks` intake-only API

This document describes the first API surface for agent work intake.

This endpoint does not execute work, apply patches, call brokers, trigger paper orders, change live config, render dashboard controls, create mobile approval behavior, auto-merge, or start a runtime worker.

## Purpose

Agent PR 1 created the request contract.
Agent PR 2 created the scope guard.
Agent PR 3 created patch-only approval plus local audit evidence.
Agent PR 4 created the local CLI.
Agent PR 5 created local task storage.
Agent PR 6 exposes intake-only task submission over HTTP.

```text
POST /agent/tasks
  -> normalize_agent_work_request
  -> assess_agent_scope
  -> approve_agent_work
  -> write_agent_evidence
  -> persist_agent_task
  -> response with safe flags
```

## Endpoint

```text
POST /agent/tasks
```

## Request body

The body is an AgentWorkRequest JSON payload.

Optional API-only fields:

```text
human_approved: boolean
approved_by: string
```

These fields are removed before normalizing the AgentWorkRequest contract.

Example:

```json
{
  "schema_version": 1,
  "source_agent": "gsd",
  "action": "GENERATE_TESTS",
  "title": "Add API tests",
  "scope": "Add deterministic tests for agent task intake.",
  "allowed_paths": ["tests/"],
  "requested_paths": ["tests/test_agent_tasks_api.py"],
  "forbidden_paths": [".env", "credentials.py", "broker_contract/"],
  "requires_human_approval": false,
  "metadata": {
    "project": "algotradify"
  }
}
```

## Response body

The response includes:

```text
contract
status
accepted
work_id
scope_decision
approval_decision
evidence_ref
task_ref
metadata
read_only
is_order_action
broker_api_called
live_mode_touched
allowed_for_live_execution
```

## Status values

```text
APPROVED_FOR_PATCH
REJECTED
BLOCKED
```

## Error responses

Malformed payloads return HTTP 400:

```text
INPUT_ERROR
```

Persistence failures return HTTP 500:

```text
INTAKE_PERSISTENCE_ERROR
```

All error responses preserve safe flags:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
```

## Safety guarantees

The endpoint is intake-only.

It cannot:

```text
execute code
apply patches
run agents
call broker APIs
place paper orders
place live orders
modify orders
cancel orders
exit positions
change live config
enable live mode
auto-merge
create dashboard actions
create mobile approval behavior
```

## CORS note

This PR does not widen browser CORS methods. The route is intended as a server-side intake endpoint. Dashboard/mobile usage belongs to later scoped PRs and must explicitly review CORS and authentication.

## Stored artifacts

Valid normalized submissions write:

```text
runtime/agent_work/agent_work_latest.json
runtime/agent_work/agent_work_YYYY-MM-DD.jsonl
runtime/agent_work/tasks/<work_id>.json
runtime/agent_work/agent_task_index.json
```

Blocked/rejected valid submissions are still audited and stored.

Invalid JSON or invalid request shape is rejected before evidence/task persistence.

## What this PR does not implement

```text
No GET /agent/tasks
No GET /agent/tasks/{work_id}
No dashboard panel
No mobile approval screen
No auto-merge
No broker action
No paper order trigger
No live config change
No runtime worker
No authentication model
No CORS expansion
```

## Test command

```bash
python -m pytest tests/test_agent_tasks_api.py tests/test_agent_task_store.py tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Acceptance proof

Agent PR 6 is complete only if:

- `POST /agent/tasks` accepts safe docs/tests work
- blocked order actions remain blocked but audited
- broker API actions remain blocked
- live actions remain blocked
- human-gated work requires approval
- human-approved work remains patch-only
- malformed payloads return safe HTTP 400
- route install is idempotent
- output contains no execution/order/broker/live controls

## Next PR

```text
Agent PR 7 — Agent Task Query API
```

Agent PR 7 may expose read-only task lookup endpoints. It must still not add dashboard controls, mobile approval, auto-merge, broker actions, paper order triggers, or live config changes.

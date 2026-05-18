# Agent Patch Approval API

Status: Agent PR 9
Scope: backend patch-review decision recording only

This PR adds backend endpoints that record a human patch-review decision for an existing agent task.

## Routes

```text
POST /agent/tasks/{work_id}/approval
POST /agent/tasks/{work_id}/rejection
```

## What approval means

Approval means only this:

```text
allowed_for_patch=true
```

It does not apply a patch, run a task, call a broker, place a paper order, mutate live configuration, or merge code.

## Approval payload

```json
{
  "approved_by": "ram",
  "reason": "reviewed scope"
}
```

## Rejection payload

```json
{
  "rejected_by": "ram",
  "reason": "scope unclear"
}
```

## Stored record

Patch-review decisions are stored locally under:

```text
runtime/agent_work/approvals/{work_id}.json
```

A task can have only one recorded patch-review decision. Duplicate approval/rejection attempts return a conflict.

## Safe flags

Every approval/rejection response keeps:

```text
read_only=true
patch_approval_only=true
allowed_for_runtime_wiring=false
allowed_for_broker_api=false
allowed_for_live_execution=false
is_order_action=false
broker_api_called=false
live_mode_touched=false
real_order_id=null
```

## Failure behavior

```text
missing task -> 404
missing approved_by/rejected_by -> 400
non-object payload -> 400
blocked task approval -> 409
duplicate decision -> 409
corrupt approval record -> fail closed
```

## Tests

```bash
python -m pytest tests/test_agent_tasks_patch_approval_api.py -q
python -m pytest tests/test_agent_tasks_patch_approval_api.py tests/test_agent_tasks_query_api.py tests/test_agent_tasks_api.py tests/test_agent_approval.py tests/test_agent_task_store.py -q
```

## Explicit non-goals

```text
No patch application
No task runner
No broker call
No paper order
No live config mutation
No auto-merge
No UI controls
No mobile approval screen
```

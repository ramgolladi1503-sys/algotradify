# Agent Task Query API

Status: Agent PR 7
Scope: read-only task lookup API only

This document describes the read-only API for querying local agent task records.

This layer does not approve work, reject work, execute work, apply patches, call brokers, trigger paper orders, change live config, render dashboard controls, create mobile approval behavior, auto-merge, or start a runtime worker.

## Purpose

Agent PR 6 added intake-only `POST /agent/tasks`.
Agent PR 7 adds read-only query endpoints.

```text
GET /agent/tasks
GET /agent/tasks/{work_id}
```

## Endpoints

### List tasks

```text
GET /agent/tasks
```

Supported filters:

```text
source_agent
action
state
risk_level
created_from
created_to
limit
```

Response includes:

```text
contract
query
source_count
result_count
records
metadata
read_only
is_order_action
broker_api_called
live_mode_touched
allowed_for_live_execution
```

### Task detail

```text
GET /agent/tasks/{work_id}
```

Response includes:

```text
contract
work_id
task
metadata
read_only
is_order_action
broker_api_called
live_mode_touched
allowed_for_live_execution
```

Missing task returns safe HTTP 404:

```text
status=NOT_FOUND
message=AGENT_TASK_NOT_FOUND
read_only=true
broker_api_called=false
allowed_for_live_execution=false
```

## Safety guarantees

The query API is read-only.

It cannot:

```text
approve tasks
reject tasks
execute tasks
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

## Corrupt store behavior

Corrupt or unsafe task files return safe query errors.

The API must not silently skip corrupt files because that would make the task index lie.

## Route installation behavior

`POST /agent/tasks` and `GET /agent/tasks` share the same path with different methods.

The installer must check both path and method. A path-only check is wrong because it would prevent GET from being installed after POST.

## What this PR does not implement

```text
No approval endpoint
No rejection endpoint
No dashboard panel
No mobile approval screen
No auto-merge
No broker action
No paper order trigger
No live config change
No runtime worker
No CORS expansion
No authentication model
```

## Test command

```bash
python -m pytest tests/test_agent_tasks_query_api.py tests/test_agent_tasks_api.py tests/test_agent_task_store.py tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Acceptance proof

Agent PR 7 is complete only if:

- list endpoint returns read-only task summaries
- detail endpoint returns full read-only task record
- source/action/state/risk filters work
- limit is validated
- missing task returns safe 404
- corrupt task file fails closed
- route installation keeps POST and GET routes idempotent
- query output contains no approval/execution/order/broker/live controls

## Next PR

```text
Agent PR 8 — Read-only Dashboard Agent Panel
```

Agent PR 8 may display task records. It must not add approval buttons, reject buttons, merge buttons, patch execution, broker actions, paper order triggers, or live config controls.

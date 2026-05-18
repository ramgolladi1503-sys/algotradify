# Agent Task Store

Status: Agent PR 5
Scope: local task persistence and read-only query only

This document describes the local task store for agent work records.

This layer does not add a webhook, API endpoint, dashboard panel, mobile approval screen, auto-merge, broker action, paper order trigger, live config change, runtime wiring, or execution worker.

## Purpose

Agent PR 1 created the request contract.
Agent PR 2 created the scope guard.
Agent PR 3 created patch-only approval plus local audit evidence.
Agent PR 4 created the local CLI.
Agent PR 5 adds local queryable task records.

```text
AgentWorkRequest + AgentScopeDecision + AgentApprovalDecision + evidence_ref
  -> AgentTaskRecord
  -> runtime/agent_work/tasks/<work_id>.json
  -> runtime/agent_work/agent_task_index.json
  -> read-only query results
```

## Files

```text
agent_system/task_store.py
agent_system/__init__.py
tests/test_agent_task_store.py
docs/agent-task-store.md
docs/pr-handoffs/AGENT-PR5-grill.md
docs/pr-handoffs/AGENT-PR5-gsd.md
docs/pr-handoffs/AGENT-PR5-hermes.md
```

## Stored files

Task records:

```text
runtime/agent_work/tasks/<work_id>.json
```

Index:

```text
runtime/agent_work/agent_task_index.json
```

## Core functions

```text
build_agent_task_record()
persist_agent_task()
load_agent_task()
rebuild_agent_task_index()
query_agent_tasks()
agent_task_store_schema_contract()
```

## Query filters

```text
work_id
source_agent
action
state
risk_level
created_from
created_to
limit
```

## Safety flags

Every task record, index, and query response preserves:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
```

Task records reject unsafe approval payloads:

```text
allowed_for_broker_api=true
allowed_for_live_execution=true
allowed_for_runtime_wiring=true
```

## Duplicate handling

Same `work_id` and identical dedupe payload:

```text
status=EXISTS
```

Same `work_id` but conflicting task content:

```text
TASK_ID_CONFLICT
```

## Corrupt file handling

The task store fails closed when task files are corrupt or unsafe.

Examples:

```text
TASK_FILE_CORRUPT:<file>
TASK_FILE_NOT_OBJECT:<file>
TASK_FILE_SCHEMA_UNSUPPORTED:<file>
UNSAFE_TASK_BROKER_API_CALLED
```

Do not silently skip corrupt task files. Silent skipping would make the task index lie.

## What this PR does not implement

```text
No webhook
No API endpoint
No dashboard panel
No mobile approval screen
No auto-merge
No broker action
No paper order trigger
No live config change
No runtime worker
```

## Test command

```bash
python -m pytest tests/test_agent_task_store.py tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Acceptance proof

Agent PR 5 is complete only if:

- task record preserves safe flags
- task persistence writes task JSON and index JSON
- missing task lookup returns safe not found
- identical duplicate work ID is a no-op
- conflicting duplicate work ID blocks
- corrupt task file fails closed
- unsafe task file fails closed
- query filters work by work_id, source, action, state, risk, and time range
- query responses remain read-only and non-executing
- unsafe approval payloads cannot be stored

## Next PR

```text
Agent PR 6 — POST /agent/tasks Intake Webhook
```

Agent PR 6 may expose intake-only submission over API. It must still not add dashboard controls, mobile approval, auto-merge, broker actions, paper order triggers, or live config changes.

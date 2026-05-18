# Agent PR 5 — GSD Build Handoff

PR: Agent PR 5 — Agent Task Store

## Implemented scope

Implemented local task persistence and read-only query only.

## Files changed

```text
agent_system/task_store.py
agent_system/__init__.py
tests/test_agent_task_store.py
docs/agent-task-store.md
docs/pr-handoffs/AGENT-PR5-grill.md
docs/pr-handoffs/AGENT-PR5-gsd.md
docs/pr-handoffs/AGENT-PR5-hermes.md
```

## Implementation summary

- Added `AgentTaskRecord`.
- Added `AgentTaskStoreError`.
- Added `build_agent_task_record()`.
- Added `persist_agent_task()`.
- Added `load_agent_task()`.
- Added `rebuild_agent_task_index()`.
- Added `query_agent_tasks()`.
- Added `agent_task_store_schema_contract()`.
- Exported task store symbols from `agent_system/__init__.py`.
- Added behavior tests for task persistence, duplicate handling, corrupt files, unsafe records, filters, date ranges, and read-only flags.

## Safety boundary preserved

No API, dashboard, mobile screen, webhook, broker call, live config, paper order trigger, runtime worker, or auto-merge behavior was implemented.

## Test command

```bash
python -m pytest tests/test_agent_task_store.py tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Known limitation

This PR persists local task records but does not expose `/agent/tasks`. Agent PR 6 owns the intake webhook.

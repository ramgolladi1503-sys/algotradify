# Agent PR 7 — GSD Build Handoff

PR: Agent PR 7 — Agent Task Query API

## Implemented scope

Implemented read-only agent task query API only.

## Files changed

```text
api/agent_tasks.py
tests/test_agent_tasks_query_api.py
docs/agent-task-query-api.md
docs/pr-handoffs/AGENT-PR7-grill.md
docs/pr-handoffs/AGENT-PR7-gsd.md
docs/pr-handoffs/AGENT-PR7-hermes.md
```

## Implementation summary

- Added `agent_tasks_query_schema_contract()`.
- Added `build_agent_task_query_payload()`.
- Added `build_agent_task_detail_payload()`.
- Added method-aware route existence checks.
- Added `GET /agent/tasks`.
- Added `GET /agent/tasks/{work_id}`.
- Added query API tests.
- Added query API documentation.

## Safety boundary preserved

No dashboard, mobile screen, approval endpoint, rejection endpoint, broker call, live config, paper order trigger, runtime worker, CORS/auth expansion, or auto-merge behavior was implemented.

## Test command

```bash
python -m pytest tests/test_agent_tasks_query_api.py tests/test_agent_tasks_api.py tests/test_agent_task_store.py tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Known limitation

This PR exposes read-only task lookup only. Agent PR 8 owns read-only dashboard display.

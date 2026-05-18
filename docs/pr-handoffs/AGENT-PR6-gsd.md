# Agent PR 6 — GSD Build Handoff

PR: Agent PR 6 — POST /agent/tasks Intake Webhook

## Implemented scope

Implemented the intake-only `POST /agent/tasks` API route.

## Files changed

```text
api/agent_tasks.py
api/server.py
tests/test_agent_tasks_api.py
docs/agent-tasks-webhook.md
docs/pr-handoffs/AGENT-PR6-grill.md
docs/pr-handoffs/AGENT-PR6-gsd.md
docs/pr-handoffs/AGENT-PR6-hermes.md
```

## Implementation summary

- Added `api/agent_tasks.py`.
- Added `agent_tasks_intake_schema_contract()`.
- Added `build_agent_task_intake_payload()`.
- Added `install_agent_tasks_route()`.
- Installed route in `api/server.py` using the existing install-route pattern.
- Added API tests with `FastAPI` and `TestClient`.
- Added webhook documentation.

## Safety boundary preserved

No dashboard, mobile screen, broker call, live config, paper order trigger, runtime worker, auto-merge, or execution behavior was implemented.

## Test command

```bash
python -m pytest tests/test_agent_tasks_api.py tests/test_agent_task_store.py tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Known limitation

This PR only adds `POST /agent/tasks`. Read-only query endpoints belong to Agent PR 7.

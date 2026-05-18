# Agent PR 9 — GSD Build Handoff

PR: Agent PR 9 — Patch-only Approval API

## Implemented scope

Implemented backend patch-review decision recording for existing agent tasks.

## Files changed

```text
agent_system/patch_approval.py
agent_system/__init__.py
api/agent_tasks.py
tests/test_agent_tasks_patch_approval_api.py
docs/agent-patch-approval-api.md
docs/pr-handoffs/AGENT-PR9-grill.md
docs/pr-handoffs/AGENT-PR9-gsd.md
docs/pr-handoffs/AGENT-PR9-hermes.md
```

## Implementation summary

- Added local patch approval/rejection record layer.
- Added `POST /agent/tasks/{work_id}/approval`.
- Added `POST /agent/tasks/{work_id}/rejection`.
- Extended task detail query with `patch_approval` record visibility.
- Added behavior tests for approval, rejection, missing task, missing actor, blocked task, duplicate decision, route idempotency, and no execution-control leakage.

## Safety boundary preserved

No frontend controls, patch execution, runtime worker, broker call, paper order trigger, live config mutation, auto-merge, or mobile approval behavior was added.

## Test command

```bash
python -m pytest tests/test_agent_tasks_patch_approval_api.py -q
```

## Adjacent regression command

```bash
python -m pytest tests/test_agent_tasks_patch_approval_api.py tests/test_agent_tasks_query_api.py tests/test_agent_tasks_api.py tests/test_agent_approval.py tests/test_agent_task_store.py -q
```

## Known limitation

This records patch-review decisions only. A future patch runner would require a separate scoped PR and must still avoid broker/live/order behavior.

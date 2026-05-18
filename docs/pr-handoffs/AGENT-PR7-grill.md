# Agent PR 7 — Grill Scope Review

PR: Agent PR 7 — Agent Task Query API

## Decision

Approve with narrow scope.

## Why this PR is next

Agent PR 6 added intake-only `POST /agent/tasks`. The next safe step is read-only task lookup so submitted tasks can be inspected without adding dashboard controls, mobile approval, approval endpoints, broker behavior, paper orders, live config, auto-merge, or task execution.

## Files allowed to change

```text
api/agent_tasks.py
tests/test_agent_tasks_query_api.py
docs/agent-task-query-api.md
docs/pr-handoffs/AGENT-PR7-grill.md
docs/pr-handoffs/AGENT-PR7-gsd.md
docs/pr-handoffs/AGENT-PR7-hermes.md
```

## Files forbidden to touch

```text
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

## Safety boundary

Read-only query API only. No approval endpoint, no rejection endpoint, no dashboard, no mobile approval, no broker calls, no paper orders, no live config, no auto-merge, no execution worker.

## Required behavior

- Add `GET /agent/tasks`.
- Add `GET /agent/tasks/{work_id}`.
- Support source_agent, action, state, risk_level, created_from, created_to, and limit filters.
- Return source_count and result_count metadata.
- Return safe 404 for missing task.
- Fail closed on corrupt task files.
- Preserve non-executing safe flags.
- Keep POST and GET route installation idempotent.

## Negative tests required

- missing task returns safe 404
- corrupt task file returns safe query error
- negative limit is rejected
- route install does not duplicate POST/GET routes
- query output contains no approval, execution, order, broker, live, or auto-merge controls

## Acceptance proof

```bash
python -m pytest tests/test_agent_tasks_query_api.py tests/test_agent_tasks_api.py tests/test_agent_task_store.py tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Merge blockers

Reject if this PR adds dashboard/mobile UI, approval/rejection endpoints, auto-merge, broker action, paper order trigger, live config mutation, runtime worker, CORS/auth expansion, or unrelated trading code.

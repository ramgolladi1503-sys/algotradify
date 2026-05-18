# Agent PR 6 — Grill Scope Review

PR: Agent PR 6 — POST /agent/tasks Intake Webhook

## Decision

Approve with narrow scope.

## Why this PR is next

Agent PR 1 created the request contract, PR 2 created the scope guard, PR 3 created patch-only approval and evidence, PR 4 created the local CLI, and PR 5 created the local task store. The next safe step is an intake-only HTTP endpoint that uses those layers without adding execution, broker, paper-order, dashboard, mobile, or live behavior.

## Files allowed to change

```text
api/agent_tasks.py
api/server.py
tests/test_agent_tasks_api.py
docs/agent-tasks-webhook.md
docs/pr-handoffs/AGENT-PR6-grill.md
docs/pr-handoffs/AGENT-PR6-gsd.md
docs/pr-handoffs/AGENT-PR6-hermes.md
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

Intake-only API. No execution, no patch application, no task execution worker, no dashboard, no mobile approval, no broker calls, no paper orders, no live config, no auto-merge.

## Required behavior

- Add `POST /agent/tasks`.
- Normalize AgentWorkRequest payloads.
- Assess scope.
- Apply patch-only approval.
- Write local evidence.
- Persist local task record.
- Return safe flags on success and failure.
- Keep blocked/rejected valid submissions auditable.
- Keep route installation idempotent.

## Negative tests required

- order action remains blocked
- broker API action remains blocked
- live action remains blocked
- human-gated work without approval remains rejected
- human-approved work remains patch-only
- malformed payload returns safe HTTP 400
- unknown source returns safe HTTP 400
- non-string approved_by returns safe HTTP 400
- output contains no execution/order/broker/live controls

## Acceptance proof

```bash
python -m pytest tests/test_agent_tasks_api.py tests/test_agent_task_store.py tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Merge blockers

Reject if this PR adds GET query endpoints, dashboard/mobile UI, auto-merge, broker action, paper order trigger, live config mutation, runtime worker, or unrelated trading code.

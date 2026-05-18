# Agent PR 5 — Grill Scope Review

PR: Agent PR 5 — Agent Task Store

## Decision

Approve with narrow scope.

## Why this PR is next

Agent PR 1 created the request contract, Agent PR 2 created the scope guard, Agent PR 3 created patch-only approval plus local audit evidence, and Agent PR 4 created the local CLI. The next safe step is local queryable task persistence before exposing any webhook, API, dashboard, or mobile approval surface.

## Files allowed to change

```text
agent_system/task_store.py
agent_system/__init__.py
tests/test_agent_task_store.py
docs/agent-task-store.md
docs/pr-handoffs/AGENT-PR5-grill.md
docs/pr-handoffs/AGENT-PR5-gsd.md
docs/pr-handoffs/AGENT-PR5-hermes.md
```

## Files forbidden to touch

```text
api/
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

Local task persistence and read-only query only. No API, no webhook, no dashboard, no mobile approval, no broker calls, no paper orders, no live config, no auto-merge, no execution worker.

## Required behavior

- Build local task records from request/scope/approval/evidence data.
- Persist immutable task JSON files under `runtime/agent_work/tasks/`.
- Maintain a local read-only index file.
- Query by work_id, source_agent, action, state, risk_level, created_at range, and limit.
- Return read-only query metadata.
- Treat identical duplicate work ID as no-op.
- Block conflicting duplicate work IDs.
- Fail closed on corrupt or unsafe task files.
- Preserve non-executing safe flags.

## Negative tests required

- corrupt task file blocks index rebuild
- unsafe task file blocks index rebuild
- duplicate identical task is no-op
- duplicate conflicting task blocks
- missing task returns safe not found
- unsafe approval payload cannot be stored
- negative query limit blocks
- query output remains read-only/non-executing

## Acceptance proof

```bash
python -m pytest tests/test_agent_task_store.py tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Merge blockers

Reject if this PR adds API, webhook, dashboard, mobile approval, broker action, paper order trigger, live config mutation, auto-merge, or unrelated trading code.

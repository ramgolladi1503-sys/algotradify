# Agent PR 9 — Grill Scope Review

PR: Agent PR 9 — Patch-only Approval API

## Decision

Approve with strict backend-only scope.

## Why this PR is next

Agent PR 8 added a read-only task dashboard. The next safe step is backend patch-review decision recording for existing agent tasks.

## Files allowed to change

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

## Files forbidden to touch

```text
frontend/
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

Record-only patch approval/rejection. No patch application, task runner, broker call, paper order trigger, live config mutation, auto-merge, mobile approval, or UI controls.

## Required behavior

- Add `POST /agent/tasks/{work_id}/approval`.
- Add `POST /agent/tasks/{work_id}/rejection`.
- Require existing task.
- Require `approved_by` or `rejected_by`.
- Allow human-gated accepted tasks to become approved for patch only.
- Block approving blocked tasks.
- Persist exactly one local decision record per task.
- Keep all broker/live/runtime/order flags false.

## Negative tests required

- missing task returns 404
- missing actor returns 400
- non-object payload returns 400
- blocked task approval returns 409
- duplicate decision returns 409
- output contains no execution controls

## Merge blockers

Reject if this PR adds frontend controls, patch execution, runtime worker, broker behavior, paper-order behavior, live config behavior, auto-merge, or unrelated trading code.

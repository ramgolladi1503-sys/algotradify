# Agent PR 10 — Grill Scope Review

PR: Agent PR 10 — Dashboard Patch Approval Controls

## Decision

Approve with narrow frontend-only scope.

## Why this PR is next

Agent PR 9 added backend patch-review approval/rejection endpoints. The next safe step is minimal dashboard controls that call those endpoints and record patch-review decisions only.

## Files allowed to change

```text
frontend/agentTaskPanel.jsx
tests/test_agent_task_panel_ui.py
docs/dashboard-patch-approval-controls.md
docs/pr-handoffs/AGENT-PR10-grill.md
docs/pr-handoffs/AGENT-PR10-gsd.md
docs/pr-handoffs/AGENT-PR10-hermes.md
```

## Files forbidden to touch

```text
api/
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

Frontend patch-review recording controls only. No backend changes, no patch execution, no task runner, no broker calls, no paper orders, no live config, no auto-merge, no mobile approval.

## Required behavior

- Show `Record Patch Approval`.
- Show `Record Patch Rejection`.
- Call `/agent/tasks/{work_id}/approval`.
- Call `/agent/tasks/{work_id}/rejection`.
- Require safe task flags before rendering record controls.
- Display latest patch-review API result.
- Keep all order/broker/live/merge/run wording out of the control surface.

## Known limitation

If frontend and API are on different origins, a later tiny backend PR must allow CORS `POST` for the existing dashboard origin.

## Negative tests required

- controls call only approval/rejection endpoints
- safety flags are still visible
- no run/execute/merge/order/broker/live controls appear
- fixture still claims no execution permissions

## Merge blockers

Reject if this PR adds backend route changes, CORS changes, patch execution, runtime worker, broker behavior, paper-order behavior, live config behavior, auto-merge, or unrelated trading code.

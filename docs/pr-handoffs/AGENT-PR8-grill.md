# Agent PR 8 — Grill Scope Review

PR: Agent PR 8 — Read-only Dashboard Agent Panel

## Decision

Approve with narrow scope.

## Why this PR is next

Agent PR 7 added read-only task query endpoints. The next safe step is displaying those records in Control Tower without adding any mutation controls.

## Files allowed to change

```text
frontend/agentTaskPanel.jsx
frontend/main.jsx
tests/test_agent_task_panel_ui.py
docs/dashboard-agent-panel.md
docs/pr-handoffs/AGENT-PR8-grill.md
docs/pr-handoffs/AGENT-PR8-gsd.md
docs/pr-handoffs/AGENT-PR8-hermes.md
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

Frontend display only. No backend route changes, no approval/rejection controls, no task mutation, no broker calls, no paper orders, no live config, no auto-merge, no runtime worker.

## Required behavior

- Fetch `/agent/tasks?limit=20`.
- Render agent task query metadata.
- Render task record rows.
- Render safety flags visibly.
- Preserve read-only status in the UI.
- Avoid any approval, rejection, execution, order, broker, live, or merge controls.

## Negative tests required

- panel is wired into Control Tower
- panel fetches read-only endpoint
- panel renders safety fields
- panel contains no mutation/execution controls
- fixture snapshot preserves safe flags

## Acceptance proof

```bash
python -m pytest tests/test_agent_task_panel_ui.py tests/test_agent_tasks_query_api.py tests/test_agent_tasks_api.py -q
```

## Merge blockers

Reject if this PR adds backend API changes, approval/rejection controls, patch execution, broker action, paper order trigger, live config mutation, auto-merge, or unrelated trading code.

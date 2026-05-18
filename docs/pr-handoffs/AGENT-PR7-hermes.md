# Agent PR 7 — Hermes Post-Code Review

PR: Agent PR 7 — Agent Task Query API

## Review result

Approve for PR review.

## Scope compliance

Changed files match the approved scope.

Forbidden files were not touched.

## Actual changed files

```text
api/agent_tasks.py
tests/test_agent_tasks_query_api.py
docs/agent-task-query-api.md
docs/pr-handoffs/AGENT-PR7-grill.md
docs/pr-handoffs/AGENT-PR7-gsd.md
docs/pr-handoffs/AGENT-PR7-hermes.md
```

## Safety review

No broker, LIVE, dashboard, mobile approval, paper-order trigger, runtime worker, strategy, ranker, approval endpoint, rejection endpoint, CORS/auth expansion, or auto-merge behavior was added.

Query responses preserve:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
```

## Test review

Tests prove behavior, not just object shape:

- list endpoint returns read-only task summaries
- detail endpoint returns full read-only task record
- source/action/state/risk filters work
- limit is validated
- missing task returns safe 404
- corrupt task file fails closed
- route installation keeps POST and GET routes idempotent
- query helper exposes no execution flags
- query output contains no approval/execution/order/broker/live/auto-merge controls

## Remaining risk

Dashboard display does not exist yet. Agent PR 8 may add a read-only dashboard panel, but must not add approval buttons, rejection buttons, merge buttons, patch execution, broker actions, paper order triggers, live config controls, or auto-merge.

## Reject before merge if

- Any dashboard/mobile implementation appears.
- Any approval/rejection endpoint appears.
- Broker/live/paper execution code appears.
- Query responses expose approval, order, broker, live, or auto-merge controls.
- Corrupt task files are silently skipped.

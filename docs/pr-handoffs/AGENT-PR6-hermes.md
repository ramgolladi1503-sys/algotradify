# Agent PR 6 — Hermes Post-Code Review

PR: Agent PR 6 — POST /agent/tasks Intake Webhook

## Review result

Approve for PR review.

## Scope compliance

Changed files match the approved scope.

Forbidden files were not touched.

## Actual changed files

```text
api/agent_tasks.py
api/server.py
tests/test_agent_tasks_api.py
docs/agent-tasks-webhook.md
docs/pr-handoffs/AGENT-PR6-grill.md
docs/pr-handoffs/AGENT-PR6-gsd.md
docs/pr-handoffs/AGENT-PR6-hermes.md
```

## Safety review

No broker, LIVE, dashboard, mobile approval, paper-order trigger, runtime worker, strategy, ranker, auto-merge, or patch execution behavior was added.

The endpoint preserves:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
```

## Test review

Tests prove behavior, not just object shape:

- safe docs/tests request is approved and persisted
- order action is blocked but audited
- broker API action is blocked
- live action is blocked
- human-gated request without approval is rejected
- human-approved request remains patch-only
- malformed shape returns safe HTTP 400
- unknown source returns safe HTTP 400
- non-string approved_by returns safe HTTP 400
- route install is idempotent
- output has no execution/order/broker/live controls

## Remaining risk

No read-only query API exists yet. Agent PR 7 must add only `GET /agent/tasks` and `GET /agent/tasks/{work_id}` without approval buttons, dashboard controls, broker actions, paper order triggers, live config, or auto-merge.

## Reject before merge if

- Any dashboard/mobile implementation appears.
- Broker/live/paper execution code appears.
- GET query endpoints sneak into this PR.
- The route starts applying patches or executing tasks.
- CORS/auth changes appear without explicit scope.

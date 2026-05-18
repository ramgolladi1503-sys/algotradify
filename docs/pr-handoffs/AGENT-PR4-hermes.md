# Agent PR 4 — Hermes Post-Code Review

PR: Agent PR 4 — Local Agent Work CLI

## Review result

Approve for PR review.

## Scope compliance

Changed files match the approved scope.

Forbidden files were not touched.

## Actual changed files

```text
scripts/submit_agent_work.py
docs/samples/gsd-agent-work.json
docs/samples/hermes-agent-work.json
docs/samples/grill-agent-work.json
tests/test_submit_agent_work.py
docs/local-agent-work-cli.md
docs/pr-handoffs/AGENT-PR4-grill.md
docs/pr-handoffs/AGENT-PR4-gsd.md
docs/pr-handoffs/AGENT-PR4-hermes.md
```

## Safety review

No broker, LIVE, API, dashboard, mobile approval, paper-order trigger, runtime wiring, strategy, ranker, task store, webhook, or auto-merge behavior was added.

CLI results preserve:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
```

## Test review

Tests prove behavior, not just object shape:

- missing payload exits blocked
- malformed JSON exits blocked
- non-object JSON exits blocked
- approved docs/tests request exits zero and writes evidence
- blocked order action exits blocked and writes rejected evidence
- human-gated request without approval exits rejected
- human-gated request with approval exits approved for patch only
- missing approved_by exits rejected
- forbidden path exits blocked
- output contains no order or broker controls

## Remaining risk

No queryable task store exists yet. Agent PR 5 must add local task storage without adding webhook/API/dashboard/mobile/broker/live behavior.

## Reject before merge if

- Any API/webhook/dashboard/mobile implementation appears.
- Broker/live/paper execution code appears.
- Task store sneaks into this PR.
- Any CLI output exposes order/broker/live controls.
- Any exit path hides unsafe behavior as success.

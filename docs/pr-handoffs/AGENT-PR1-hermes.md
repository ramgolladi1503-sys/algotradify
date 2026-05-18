# Agent PR 1 — Hermes Post-Code Review

PR: Agent PR 1 — Agent Work Contract Foundation

## Review result

Approve for PR review.

## Scope compliance

Changed files match the approved scope.

Forbidden files were not touched.

## Actual changed files

```text
agent_system/__init__.py
agent_system/work_contract.py
tests/test_agent_work_contract.py
docs/agent-work-contract.md
docs/pr-handoffs/AGENT-PR1-grill.md
docs/pr-handoffs/AGENT-PR1-gsd.md
docs/pr-handoffs/AGENT-PR1-hermes.md
```

## Safety review

No broker, LIVE, API, dashboard, mobile approval, paper-order trigger, runtime wiring, strategy, ranker, or auto-merge behavior was added.

The contract exposes safe defaults:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
real_order_id=null
```

## Test review

Tests prove behavior, not just object shape:

- valid normalization
- alias normalization
- action normalization
- missing requested paths blocked
- path field type validation
- unknown source/action blocked
- empty title/scope blocked
- metadata type validation
- unsupported schema version blocked
- forbidden actions are known but not safe
- safe and forbidden action sets are disjoint
- deterministic work ID behavior
- schema contract safe defaults

## Remaining risk

The contract does not yet enforce source/action permissions or path restrictions. That is the next PR: Agent PR 2 — Agent Scope Guard.

## Reject before merge if

- API/webhook/dashboard/mobile implementation appears.
- Broker/live/paper execution code appears.
- Scope guard logic is added into this PR.
- Forbidden actions are treated as safe.
- Tests are weakened to shape-only assertions.

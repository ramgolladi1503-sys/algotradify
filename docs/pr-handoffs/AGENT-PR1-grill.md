# Agent PR 1 — Grill Scope Review

PR: Agent PR 1 — Agent Work Contract Foundation

## Decision

Approve with narrow scope.

## Why this PR is next

The merged agent runtime intake scope says the safe first step is the canonical contract. Without it, later scope guard, approval, evidence, webhook, dashboard, or mobile approval work has no stable input shape.

## Files allowed to change

```text
agent_system/__init__.py
agent_system/work_contract.py
tests/test_agent_work_contract.py
docs/agent-work-contract.md
docs/pr-handoffs/AGENT-PR1-grill.md
docs/pr-handoffs/AGENT-PR1-gsd.md
docs/pr-handoffs/AGENT-PR1-hermes.md
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

Contract-only. No API, no UI, no webhook, no approval engine, no evidence journal, no broker calls, no paper orders, no live config, no auto-merge.

## Required behavior

- Normalize source agents.
- Normalize action names.
- Require title, scope, and requested paths.
- Preserve allowed/requested/forbidden path lists.
- Generate deterministic work IDs.
- Keep schema version explicit.
- Represent forbidden actions so later scope guard can block them cleanly.
- Expose safe defaults in schema contract.

## Negative tests required

- missing source agent
- unknown source agent
- missing action
- unknown action
- empty title
- empty scope
- missing requested paths
- path fields passed as strings
- non-string path entries
- non-object metadata
- unsupported schema version
- forbidden actions not included in safe action set

## Acceptance proof

```bash
python -m pytest tests/test_agent_work_contract.py -q
```

## Merge blockers

Reject if this PR adds API/webhook/dashboard/mobile/paper/broker/live behavior or touches unrelated trading layers.

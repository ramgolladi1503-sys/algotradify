# Agent PR 2 — Grill Scope Review

PR: Agent PR 2 — Agent Scope Guard

## Decision

Approve with narrow scope.

## Why this PR is next

Agent PR 1 created the deterministic request contract but intentionally did not block source/action mismatches, forbidden trading actions, forbidden paths, or high-risk paths. Agent PR 2 must add that safety boundary before approval, evidence, webhook, dashboard, or mobile approval can exist.

## Files allowed to change

```text
agent_system/scope_guard.py
agent_system/__init__.py
tests/test_agent_scope_guard.py
docs/agent-scope-guard.md
docs/pr-handoffs/AGENT-PR2-grill.md
docs/pr-handoffs/AGENT-PR2-gsd.md
docs/pr-handoffs/AGENT-PR2-hermes.md
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

Scope guard only. No API, no UI, no webhook, no approval engine, no evidence journal, no task store, no broker calls, no paper orders, no live config, no auto-merge.

## Required behavior

- Enforce source/action permission matrix.
- Block global forbidden actions.
- Block order, broker API, and live actions with explicit reasons.
- Block forbidden paths.
- Block requested paths outside allowed paths.
- Require human approval for high-risk paths.
- Approve docs/tests-only scope for patch.
- Preserve non-executing safe flags on every decision.

## Negative tests required

- Grill cannot generate patch.
- Hermes cannot touch broker/runtime path.
- GSD cannot place order.
- Manual cannot bypass forbidden order action.
- Broker API action blocks.
- Live action blocks.
- Forbidden path blocks.
- Outside allowed path blocks.
- High-risk path requires human approval.
- Docs/tests-only scope is patch-approved.

## Acceptance proof

```bash
python -m pytest tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Merge blockers

Reject if this PR adds approval, evidence, task store, API, webhook, dashboard, mobile approval, auto-merge, paper order trigger, broker call, live config mutation, or unrelated trading code.

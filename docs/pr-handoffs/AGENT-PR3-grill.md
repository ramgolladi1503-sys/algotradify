# Agent PR 3 — Grill Scope Review

PR: Agent PR 3 — Agent Approval and Evidence Journal

## Decision

Approve with narrow scope.

## Why this PR is next

Agent PR 1 created the request contract. Agent PR 2 created the scope guard. The next safe step is converting scope decisions into patch-only approval decisions and writing local audit evidence.

## Files allowed to change

```text
agent_system/approval.py
agent_system/evidence.py
agent_system/__init__.py
tests/test_agent_approval.py
tests/test_agent_evidence.py
docs/agent-approval-evidence.md
docs/pr-handoffs/AGENT-PR3-grill.md
docs/pr-handoffs/AGENT-PR3-gsd.md
docs/pr-handoffs/AGENT-PR3-hermes.md
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

Approval/evidence only. No task store, no CLI, no API, no webhook, no dashboard, no mobile approval, no broker calls, no paper orders, no live config, no auto-merge.

## Required behavior

- Block approval for blocked scope decisions.
- Require human approval where scope guard says human approval is required.
- Require non-empty `approved_by` when human approval is claimed.
- Never grant runtime wiring, broker API, live execution, or order-action rights.
- Write local latest JSON evidence.
- Append local daily JSONL evidence.
- Allow rejected work to be audited.
- Preserve safe flags in evidence.

## Negative tests required

- blocked scope cannot be approved
- human approval required but missing rejects
- approved_by missing rejects
- broker/live/runtime/order flags reject
- rejected work can be audited
- evidence safety mutation rejects
- evidence writes latest and daily files

## Acceptance proof

```bash
python -m pytest tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Merge blockers

Reject if this PR adds task store, CLI, API, webhook, dashboard, mobile approval, auto-merge, broker action, paper order trigger, live config mutation, or unrelated trading code.

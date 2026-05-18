# Agent PR 2 — GSD Build Handoff

PR: Agent PR 2 — Agent Scope Guard

## Implemented scope

Implemented the approved scope guard layer only.

## Files changed

```text
agent_system/scope_guard.py
agent_system/__init__.py
tests/test_agent_scope_guard.py
docs/agent-scope-guard.md
docs/pr-handoffs/AGENT-PR2-grill.md
docs/pr-handoffs/AGENT-PR2-gsd.md
docs/pr-handoffs/AGENT-PR2-hermes.md
```

## Implementation summary

- Added `AgentScopeDecision` dataclass.
- Added source/action permission matrix.
- Added forbidden path prefixes.
- Added high-risk path prefixes.
- Added low-risk docs/tests path handling.
- Added `assess_agent_scope()`.
- Added `agent_scope_guard_schema_contract()`.
- Exported scope guard symbols from `agent_system/__init__.py`.
- Added behavior tests for blocking and approval decisions.

## Safety boundary preserved

No API, dashboard, mobile screen, webhook, task store, approval engine, evidence journal, broker call, live config, paper order trigger, or auto-merge behavior was implemented.

## Test command

```bash
python -m pytest tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Known limitation

This PR only assesses scope. It does not perform human approval or write evidence. That belongs to Agent PR 3 — Agent Approval and Evidence Journal.

# Agent PR 1 — GSD Build Handoff

PR: Agent PR 1 — Agent Work Contract Foundation

## Implemented scope

Implemented the approved contract-only foundation.

## Files changed

```text
agent_system/__init__.py
agent_system/work_contract.py
tests/test_agent_work_contract.py
docs/agent-work-contract.md
docs/pr-handoffs/AGENT-PR1-grill.md
docs/pr-handoffs/AGENT-PR1-gsd.md
docs/pr-handoffs/AGENT-PR1-hermes.md
```

## Implementation summary

- Added `AgentSource`, `AgentAction`, and `AgentRiskLevel` enums.
- Added safe and forbidden action sets.
- Added immutable `AgentWorkRequest` dataclass.
- Added `normalize_agent_work_request()` for deterministic validation and normalization.
- Added `build_agent_work_id()` using stable identity fields.
- Added `agent_work_schema_contract()` exposing safe defaults.
- Added behavior tests for valid requests, invalid shapes, deterministic ID behavior, safe/forbidden action separation, and schema contract safety.

## Safety boundary preserved

No API, dashboard, mobile screen, webhook, task store, approval engine, evidence journal, broker call, live config, paper order trigger, or auto-merge behavior was implemented.

## Test command

```bash
python -m pytest tests/test_agent_work_contract.py -q
```

## Known limitation

This PR does not block forbidden actions. It only represents them. Blocking belongs to Agent PR 2 — Agent Scope Guard.

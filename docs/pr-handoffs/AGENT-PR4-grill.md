# Agent PR 4 — Grill Scope Review

PR: Agent PR 4 — Local Agent Work CLI

## Decision

Approve with narrow scope.

## Why this PR is next

Agent PR 1 created the request contract, Agent PR 2 created the scope guard, and Agent PR 3 created patch-only approval plus local audit evidence. The next safe step is a local CLI that invokes those layers without adding webhook, API, UI, task store, broker, paper-order, or live behavior.

## Files allowed to change

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

Local CLI only. No task store, no API, no webhook, no dashboard, no mobile approval, no broker calls, no paper orders, no live config, no auto-merge, no execution worker.

## Required behavior

- Read AgentWorkRequest JSON from local file.
- Normalize request.
- Assess scope.
- Run patch-only approval.
- Write local audit evidence for valid normalized submissions.
- Return explicit exit codes.
- Print JSON output when requested.
- Preserve non-executing safe flags.

## Negative tests required

- missing payload file exits blocked
- malformed JSON exits blocked
- non-object JSON exits blocked
- approved docs/tests request exits zero
- blocked order action exits blocked
- human-gated request without approval exits rejected
- human-gated request with approval exits approved for patch only
- forbidden path request exits blocked
- output contains no order or broker controls

## Acceptance proof

```bash
python -m pytest tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Merge blockers

Reject if this PR adds task store, API, webhook, dashboard, mobile approval, broker action, paper order trigger, live config mutation, auto-merge, or unrelated trading code.

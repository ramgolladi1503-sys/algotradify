# Agent Approval and Evidence Journal

Status: Agent PR 3
Scope: patch-only approval decisions and local audit evidence only

This document describes the patch-only approval layer and local audit evidence writer for agent work intake.

This layer does not add a task store, CLI, webhook, API endpoint, dashboard panel, mobile approval screen, auto-merge, broker action, paper order trigger, live config change, runtime wiring, or execution worker.

## Purpose

Agent PR 1 created the request contract.
Agent PR 2 created the scope guard.
Agent PR 3 converts scope decisions into patch-only approval decisions and writes local audit evidence.

```text
AgentWorkRequest
  -> AgentScopeDecision
  -> AgentApprovalDecision
  -> local audit evidence JSON/JSONL
```

## Files

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

## Approval rules

`approve_agent_work()` returns `AgentApprovalDecision`.

Allowed final states:

```text
APPROVED_FOR_PATCH
REJECTED
```

Approval can only grant:

```text
allowed_for_patch=true
```

Approval can never grant:

```text
allowed_for_runtime_wiring=true
allowed_for_broker_api=true
allowed_for_live_execution=true
is_order_action=true
broker_api_called=true
live_mode_touched=true
```

## Approval blockers

Approval rejects when:

```text
SCOPE_DECISION_NOT_ACCEPTED
BLOCKED_WORK_CANNOT_BE_APPROVED
HUMAN_APPROVAL_REQUIRED
APPROVED_BY_REQUIRED
ORDER_ACTION_FORBIDDEN
BROKER_API_FORBIDDEN
LIVE_EXECUTION_FORBIDDEN
RUNTIME_WIRING_FORBIDDEN
```

## Human approval behavior

Low-risk docs/tests work can be approved without explicit human approval when the scope guard already approved patch scope.

Medium/high-risk accepted work requires:

```text
human_approved=true
approved_by=<non-empty reviewer>
```

Even then, the result is still patch-only. It does not permit runtime wiring, broker API calls, live execution, or order actions.

## Evidence behavior

`write_agent_evidence()` writes:

```text
runtime/agent_work/agent_work_latest.json
runtime/agent_work/agent_work_YYYY-MM-DD.jsonl
```

The latest file is atomically replaced.
The daily file is append-only JSONL.

Evidence includes:

```text
schema_version
created_at
request
scope_decision
approval_decision
safety
metadata
```

Evidence can record both approved and rejected work. Rejected work must be auditable too.

## Evidence safety flags

Every evidence payload includes:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
```

Unsafe evidence safety flags raise `AgentEvidenceError`.

## What this PR does not implement

```text
No task store
No local CLI
No webhook
No API endpoint
No dashboard panel
No mobile approval screen
No auto-merge
No broker action
No paper order trigger
No live config change
No runtime worker
```

## Test command

```bash
python -m pytest tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Acceptance proof

Agent PR 3 is complete only if:

- blocked scope cannot be approved
- human approval is required for waiting-human-approval decisions
- approved_by is required when human approval is claimed
- approved decisions remain patch-only
- broker/live/runtime/order flags cannot be approved
- evidence writes latest JSON and daily JSONL
- rejected work can be audited
- evidence safety flags remain explicit

## Next PR

```text
Agent PR 4 — Local Agent Work CLI
```

Agent PR 4 may invoke the contract, scope guard, approval layer, and evidence writer from a local script. It must still not add webhook, dashboard, mobile approval, broker actions, paper order triggers, or live config changes.

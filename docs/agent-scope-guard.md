# Agent Scope Guard

Status: Agent PR 2
Scope: request scope assessment only

This document describes the first safety guard after the Agent PR 1 work contract.

This layer does not approve work for runtime execution, execute work, expose APIs, render dashboard/mobile UI, trigger paper orders, call broker APIs, change live config, create task storage, write evidence, or merge pull requests.

## Purpose

The purpose of Agent PR 2 is to decide whether a normalized `AgentWorkRequest` is blocked, approved for low-risk patch work, or waiting for human approval.

```text
AgentWorkRequest
  -> assess_agent_scope
  -> AgentScopeDecision
```

That is all.

## Files

```text
agent_system/scope_guard.py
agent_system/__init__.py
tests/test_agent_scope_guard.py
docs/agent-scope-guard.md
docs/pr-handoffs/AGENT-PR2-grill.md
docs/pr-handoffs/AGENT-PR2-gsd.md
docs/pr-handoffs/AGENT-PR2-hermes.md
```

## Source/action permission matrix

### Grill Me

Allowed:

```text
CRITIQUE_SCOPE
REVIEW_PR
AUDIT_RISK
FIND_FAKE_PROGRESS
```

Forbidden:

```text
GENERATE_PATCH
FIX_TEST_FAILURE
PLACE_ORDER
CALL_BROKER_API
ENABLE_LIVE
```

### Hermes

Allowed:

```text
DESIGN_ARCHITECTURE
DEFINE_CONTRACT
MAP_WORKFLOW
CREATE_ACCEPTANCE_GATES
UPDATE_DOCS
```

Forbidden:

```text
PLACE_ORDER
CALL_BROKER_API
CHANGE_LIVE_CONFIG
```

### GSD

Allowed:

```text
PLAN_PR
GENERATE_TESTS
GENERATE_PATCH
FIX_TEST_FAILURE
UPDATE_DOCS
```

Forbidden:

```text
PLACE_ORDER
CALL_BROKER_API
ENABLE_LIVE
CHANGE_LIVE_CONFIG
```

### Manual

Manual can submit any known action into the guard, but global forbidden actions still block.

Manual is not a backdoor.

## Global forbidden actions

These are always blocked:

```text
PLACE_ORDER
MODIFY_ORDER
CANCEL_ORDER
EXIT_POSITION
ENABLE_LIVE
DISABLE_RISK_GATE
CHANGE_BROKER_CONFIG
CHANGE_LIVE_CONFIG
CALL_BROKER_API
```

## Forbidden paths

These path prefixes are always blocked:

```text
.env
credentials.py
config/secrets
runtime/live
logs/broker
broker_contract/
execution_safety/live
execution_readiness/live
paper_broker/live
```

## High-risk paths

These paths are not automatically patch-approved. If not otherwise forbidden, they require human approval:

```text
broker_contract/
execution_safety/
execution_readiness/
paper_trading/
core/risk
core/execution
config/
main.py
run_live.sh
```

Note: some high-risk paths are also forbidden. Forbidden wins.

## Low-risk paths

Docs/tests-only work may be patch-approved by the guard:

```text
docs/
tests/
```

A low-risk decision still does not execute anything. It only says the request is allowed for patch workflow.

## Decision states

```text
BLOCKED
WAITING_HUMAN_APPROVAL
APPROVED_FOR_PATCH
```

## Safe decision defaults

Every `AgentScopeDecision` preserves:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_runtime_wiring=false
allowed_for_broker_api=false
allowed_for_live_execution=false
```

## Blocker examples

```text
ACTION_NOT_ALLOWED_FOR_SOURCE_AGENT
ACTION_FORBIDDEN
ORDER_ACTION_FORBIDDEN
BROKER_API_FORBIDDEN
LIVE_ACTION_FORBIDDEN
REQUESTED_PATHS_MISSING
FORBIDDEN_PATH_REQUESTED
REQUESTED_PATH_EXPLICITLY_FORBIDDEN
REQUESTED_PATH_OUTSIDE_ALLOWED_PATHS
```

## What this PR does not implement

```text
No approval engine
No evidence journal
No task store
No CLI
No webhook
No API endpoint
No dashboard panel
No mobile approval screen
No auto-merge
No broker action
No paper order trigger
No live config change
```

## Test command

```bash
python -m pytest tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Acceptance proof

Agent PR 2 is complete only if:

- source/action permission matrix is enforced
- forbidden actions are blocked globally
- order/broker/live actions are blocked with explicit reasons
- forbidden paths are blocked
- requested paths outside allowed paths are blocked
- high-risk paths require human approval
- docs/tests-only requests can be approved for patch
- every decision remains non-executing and live/broker disabled

## Next PR

```text
Agent PR 3 — Agent Approval and Evidence Journal
```

Agent PR 3 must convert scope decisions into approval decisions and write local audit evidence. It must still not add webhook, dashboard, mobile approval, broker actions, paper order triggers, or live config.

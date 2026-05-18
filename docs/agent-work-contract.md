# Agent Work Contract

Status: Agent PR 1
Scope: contract foundation only

This document describes the canonical agent work request contract for algotradify.

This layer does not approve work, execute work, call APIs, touch broker code, trigger paper orders, change live config, create dashboard controls, or merge pull requests.

## Purpose

The purpose of Agent PR 1 is to define one deterministic input contract that future agent intake layers can use before any guard, approval, evidence, webhook, dashboard, or mobile approval screen exists.

```text
agent payload
  -> normalize_agent_work_request
  -> AgentWorkRequest
  -> build_agent_work_id
```

That is all.

## Files

```text
agent_system/__init__.py
agent_system/work_contract.py
tests/test_agent_work_contract.py
docs/agent-work-contract.md
```

## Source agents

Allowed source agents:

```text
gsd
hermes
grill_me
manual
```

Aliases are normalized:

```text
Grill Me -> grill_me
grill -> grill_me
GSD -> gsd
Hermes -> hermes
Manual -> manual
```

Unknown source agents are blocked during normalization.

## Actions

Safe actions are representable as safe contract actions:

```text
CRITIQUE_SCOPE
REVIEW_PR
AUDIT_RISK
FIND_FAKE_PROGRESS
DESIGN_ARCHITECTURE
DEFINE_CONTRACT
MAP_WORKFLOW
CREATE_ACCEPTANCE_GATES
PLAN_PR
GENERATE_TESTS
GENERATE_PATCH
FIX_TEST_FAILURE
UPDATE_DOCS
```

Forbidden actions are also representable:

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

This is deliberate.

A forbidden action should not become an unknown string. It should normalize into a known action so the next layer, `agent_system/scope_guard.py`, can block it with structured reasons.

## Request shape

Required fields:

```text
schema_version
source_agent
action
title
scope
requested_paths
```

Optional fields:

```text
allowed_paths
forbidden_paths
requires_human_approval
metadata
```

Example:

```json
{
  "schema_version": 1,
  "source_agent": "gsd",
  "action": "GENERATE_TESTS",
  "title": "Add tests for agent work contract",
  "scope": "Add deterministic tests for request normalization and work ID generation.",
  "allowed_paths": ["tests/"],
  "requested_paths": ["tests/test_agent_work_contract.py"],
  "forbidden_paths": ["credentials.py", ".env", "broker_contract/"],
  "requires_human_approval": false,
  "metadata": {
    "project": "algotradify"
  }
}
```

## Deterministic work ID

`build_agent_work_id()` uses only stable identity fields:

```text
schema_version
source_agent
action
title
scope
requested_paths
```

Metadata does not affect the work ID.

That means notes, caller context, or UI metadata can change without producing a different identity for the same work request.

## Validation behavior

Normalization blocks:

```text
non-object payload
unsupported schema version
missing source agent
unknown source agent
missing action
unknown action
missing title
missing scope
missing requested paths
path fields that are strings instead of lists
non-string path entries
non-object metadata
```

Normalization does not block forbidden actions. Scope guard owns that in the next PR.

## Safe defaults

The contract exposes these defaults through `agent_work_schema_contract()`:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
real_order_id=null
```

These are not execution permissions. They are contract-level safety declarations for downstream layers.

## What this PR does not implement

```text
No scope guard
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
python -m pytest tests/test_agent_work_contract.py -q
```

## Acceptance proof

Agent PR 1 is complete only if:

- valid requests normalize deterministically
- invalid request shape fails closed
- source and action names normalize consistently
- forbidden actions are known but not safe
- safe action set does not contain trading/broker/live actions
- work ID is deterministic
- schema contract exposes safe defaults

## Next PR

```text
Agent PR 2 — Agent Scope Guard
```

Agent PR 2 must block forbidden actions, forbidden paths, source/action mismatches, broker/live/config/secrets paths, and high-risk paths requiring human approval.

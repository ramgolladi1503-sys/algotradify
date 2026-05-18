# Local Agent Work CLI

Status: Agent PR 4
Scope: local submission CLI only

This document describes the local-only CLI for submitting agent work payloads through the existing safe intake layers.

This layer does not add a task store, webhook, API endpoint, dashboard panel, mobile approval screen, auto-merge, broker action, paper order trigger, live config change, runtime wiring, or execution worker.

## Purpose

Agent PR 1 created the request contract.
Agent PR 2 created the scope guard.
Agent PR 3 created patch-only approval and local audit evidence.
Agent PR 4 adds a local CLI wrapper that calls those layers in order.

```text
payload JSON
  -> normalize_agent_work_request
  -> assess_agent_scope
  -> approve_agent_work
  -> write_agent_evidence
  -> exit code + JSON output
```

## Command

```bash
PYTHONPATH=. python scripts/submit_agent_work.py --payload docs/samples/gsd-agent-work.json --json
```

## Flags

```text
--payload         required path to AgentWorkRequest JSON
--approve         record explicit human approval for eligible patch work
--approved-by     reviewer name required when --approve is used for human-gated work
--evidence-root   local evidence directory; default runtime/agent_work
--json            print full JSON result
```

## Exit codes

```text
0 = APPROVED_FOR_PATCH
1 = REJECTED
2 = BLOCKED or input error
3 = evidence write failure
```

## Sample payloads

```text
docs/samples/gsd-agent-work.json
docs/samples/hermes-agent-work.json
docs/samples/grill-agent-work.json
```

## Safety guarantees

Every CLI result preserves:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
```

The CLI cannot:

```text
place orders
modify orders
cancel orders
exit positions
call broker APIs
change live config
enable live mode
merge pull requests
apply patches
run an agent worker
start a webhook
write dashboard/mobile state
```

## Evidence behavior

The CLI writes local audit evidence through `write_agent_evidence()`:

```text
runtime/agent_work/agent_work_latest.json
runtime/agent_work/agent_work_YYYY-MM-DD.jsonl
```

Rejected and blocked work are also audited when the payload can be normalized and assessed.

Input errors such as missing files or invalid JSON do not write evidence because there is no valid normalized request to audit.

## Examples

Safe docs/tests request:

```bash
PYTHONPATH=. python scripts/submit_agent_work.py \
  --payload docs/samples/gsd-agent-work.json \
  --evidence-root runtime/agent_work \
  --json
```

Human-approved medium-risk request:

```bash
PYTHONPATH=. python scripts/submit_agent_work.py \
  --payload /path/to/payload.json \
  --approve \
  --approved-by ram \
  --json
```

## What this PR does not implement

```text
No task store
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
python -m pytest tests/test_submit_agent_work.py tests/test_agent_approval.py tests/test_agent_evidence.py tests/test_agent_scope_guard.py tests/test_agent_work_contract.py -q
```

## Acceptance proof

Agent PR 4 is complete only if:

- missing payload exits blocked
- malformed JSON exits blocked
- non-object JSON exits blocked
- docs/tests request exits approved
- blocked order action exits blocked
- human-gated request without approval exits rejected
- human-gated request with approval exits approved for patch only
- forbidden path request exits blocked
- CLI output has no order/broker/live controls
- evidence is written for valid normalized submissions

## Next PR

```text
Agent PR 5 — Agent Task Store
```

Agent PR 5 may persist queryable local task records. It must still not add webhook, API, dashboard, mobile approval, broker actions, paper order triggers, or live config changes.

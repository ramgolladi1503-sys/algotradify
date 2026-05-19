# PR Template and Local Developer Gate

## Status

Agent Governance PR 17.

This document describes the PR template and local developer gate for the role-based mini-agent architecture.

## Scope

PR 17 adds:

```text
PR template requirements
local developer gate core
local developer gate CLI
local developer gate tests
```

It does not add:

```text
architecture replay report
architecture audit report
agent worker
auto-merge
mobile approval
product behavior
runtime behavior
strategy/ranker/profitability work
```

Those belong to later work or remain out of scope.

## PR template

Template path:

```text
.github/pull_request_template.md
```

The template requires:

```text
Summary
Agent handoff evidence
Pre-code scope review
Files changed
Files not touched
Safety boundary
Tests added
Test commands
Acceptance proof
Post-code review
Next PR after merge
```

The template also requires exact safety-review phrases used by the local gate:

```text
Grill independent: yes
GSD followed Grill scope: yes
Hermes reviewed final diff: yes
Changed files match approved scope: yes
Forbidden files touched: no
Safety boundary preserved: yes
```

## Local developer gate

CLI path:

```text
scripts/agent_pr_gate.py
```

Example usage:

```bash
python scripts/agent_pr_gate.py \
  --task-ref AGENT-PR17 \
  --pr-body-file pr_body.md \
  --changed-files-file changed_files.txt \
  --human-approved \
  --json
```

## Gate checks

The local gate combines:

```text
PR body/template validation
PR 15 architecture gate
PR 16 changed-file scope auditor
```

The gate fails closed when:

```text
required PR body sections are missing
required PR body phrases are missing
handoff evidence is missing or invalid
changed files are outside approved scope
changed files are forbidden by handoff evidence
high-risk files are changed without human approval
```

## Safe flags

Every local gate report preserves:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
real_order_id=null
allowed_for_runtime_wiring=false
allowed_for_broker_api=false
```

## What PR 17 deliberately does not do

PR 17 does not generate full architecture replay reports.

PR 17 does not decide final merge-readiness across the entire architecture history.

PR 17 does not add product behavior or runtime behavior.

Those belong to PR 18 or remain out of scope.

## Next PR

PR 18 — Architecture Replay / Audit Report.

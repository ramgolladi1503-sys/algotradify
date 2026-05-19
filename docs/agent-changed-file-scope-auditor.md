# Changed-File Scope Auditor

## Status

Agent Governance PR 16.

This document describes the changed-file scope auditor for the role-based mini-agent architecture.

## Scope

PR 16 adds a changed-file auditor only.

It does not add:

```text
PR template gate
architecture audit report
agent worker
auto-merge
mobile approval
broker behavior
paper execution behavior
live config mutation
runtime execution behavior
```

Those belong to later PRs in the locked PR 11–18 order.

## Purpose

The auditor compares a list of changed files against approved scope from handoff artifacts.

Default scope roles:

```text
scope_owner
hermes_architect
gsd_implementer
```

A changed file is accepted only when:

```text
all required scope roles allow the file
no required scope role forbids the file
high-risk paths have explicit human approval
```

## CLI usage

Single file:

```bash
python scripts/audit_agent_changed_files.py --task-id AGENT-PR16 --changed-file docs/example.md --json
```

Multiple files:

```bash
python scripts/audit_agent_changed_files.py \
  --task-id AGENT-PR16 \
  --changed-file agent_system/changed_file_auditor.py \
  --changed-file tests/test_agent_changed_file_auditor.py \
  --human-approved \
  --json
```

From file list:

```bash
python scripts/audit_agent_changed_files.py --task-id AGENT-PR16 --changed-files-file changed_files.txt --json
```

## Auditor checks

The auditor fails closed when:

```text
changed file list is empty
changed file path is unsafe
scope handoff evidence is missing or invalid
changed file is outside approved scope
changed file is forbidden by any scope handoff
high-risk path is changed without human approval
unknown scope role is requested
```

## Safe flags

Every audit report preserves:

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

## What PR 16 deliberately does not do

PR 16 does not enforce the PR template.

PR 16 does not generate full architecture replay reports.

PR 16 does not call broker APIs, mutate runtime state, or add dashboard behavior.

PR 16 updates Agent Architecture CI only to run the changed-file auditor tests; it does not run the changed-file audit as a required merge gate yet.

## Next PR

PR 17 — PR Template and Local Developer Gate.

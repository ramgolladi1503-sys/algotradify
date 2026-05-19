# Architecture Replay / Audit Report

## Status

Agent Governance PR 18.

This document describes the final architecture replay report for the role-based mini-agent architecture wave.

## Scope

PR 18 adds deterministic reporting over the governance layers built in PR 11–17.

It reports on:

```text
role registry
workflow state machine
handoff evidence
architecture gate
PR body/template state
changed-file scope
```

It does not add:

```text
agent worker
auto-merge
mobile approval
product behavior
runtime behavior
strategy/ranker/profitability work
```

## CLI usage

JSON report:

```bash
python scripts/architecture_replay_report.py \
  --task-ref AGENT-PR18 \
  --pr-body-file pr_body.md \
  --changed-files-file changed_files.txt \
  --human-approved \
  --format json
```

Markdown report:

```bash
python scripts/architecture_replay_report.py \
  --task-ref AGENT-PR18 \
  --pr-body-file pr_body.md \
  --changed-files-file changed_files.txt \
  --human-approved \
  --format markdown
```

## Report sections

```text
role_registry
workflow_state_machine
handoff_evidence
architecture_gate
pr_body_template
changed_file_scope
```

## Fail-closed behavior

The report fails when any section fails.

Examples:

```text
missing handoff evidence fails
missing PR body sections fail
missing PR body phrases fail
changed files outside approved scope fail
forbidden changed files fail
```

## Safe flags

Every replay report preserves:

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

## What PR 18 completes

PR 18 completes the locked Agent Governance PR 11–18 wave:

```text
PR 11 — Agent Role Registry Contract
PR 12 — Role-Based Workflow State Machine
PR 13 — Role Handoff Artifact Contract
PR 14 — PR Handoff Evidence Validator
PR 15 — CI Agent Architecture Gate
PR 16 — Changed-File Scope Auditor
PR 17 — PR Template and Local Developer Gate
PR 18 — Architecture Replay / Audit Report
```

## After PR 18

After PR 18 merges, the role-based mini-agent governance wave is complete.

Normal product work may resume only with an explicit next scope and must pass through the governance gates introduced by this wave.

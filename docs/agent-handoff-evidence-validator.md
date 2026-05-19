# PR Handoff Evidence Validator

## Status

Agent Governance PR 14.

This document describes the repo-local role handoff evidence validator for the role-based mini-agent architecture.

## Scope

PR 14 validates required handoff files for one task.

It does not add:

```text
CI architecture gate
changed-file auditor
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

## Validator input

The validator expects markdown files under `docs/pr-handoffs/` containing one fenced JSON block that uses the PR 13 contract:

```text
agent_role_handoff_artifact_v1
```

Default required files for task `AGENT-PR14`:

```text
docs/pr-handoffs/AGENT-PR14-scope-owner.md
docs/pr-handoffs/AGENT-PR14-grill.md
docs/pr-handoffs/AGENT-PR14-hermes.md
docs/pr-handoffs/AGENT-PR14-gsd.md
docs/pr-handoffs/AGENT-PR14-qa-safety.md
docs/pr-handoffs/AGENT-PR14-evidence.md
```

## CLI usage

```bash
python scripts/validate_agent_handoffs.py --task-id AGENT-PR14
```

JSON output:

```bash
python scripts/validate_agent_handoffs.py --task-id AGENT-PR14 --json
```

Subset validation for development/testing:

```bash
python scripts/validate_agent_handoffs.py --task-id AGENT-PR14 --required-role grill_reviewer
```

## Validator checks

The validator fails closed when:

```text
required handoff file is missing
required role is missing
handoff file has no contract JSON payload
handoff payload fails the PR 13 artifact contract
handoff task_id does not match requested task_id
handoff role_id does not match expected file role
unsafe task_id path traversal is attempted
unknown required role is requested
```

## Contract functions

The implementation exposes:

```text
expected_handoff_paths(...)
extract_handoff_payload_from_markdown(...)
load_handoff_artifact(...)
validate_handoff_evidence(...)
agent_handoff_validator_schema_contract()
report_to_json(...)
```

## Safe flags

Every validation report preserves:

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

## Behavior guarantees

PR 14 tests prove:

```text
all required handoff files pass when valid
missing file fails and marks missing role
invalid payload fails
unsafe safe flags fail through PR 13 contract
mismatched task_id fails
mismatched role_id fails
non-contract JSON blocks are ignored
missing JSON payload fails
unsafe task_id fails
unknown required role fails
JSON report is stable
subset role validation works for focused checks
```

## What PR 14 deliberately does not do

PR 14 does not add GitHub Actions enforcement.

PR 14 does not compare changed files against allowed paths.

PR 14 does not add a PR template gate.

PR 14 does not generate full architecture replay reports.

Those enforcement features belong to PR 15–18.

## Next PR

PR 15 — CI Agent Architecture Gate.

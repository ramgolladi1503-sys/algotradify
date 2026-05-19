# Hermes Handoff — Agent Governance PR 11–18 Lock

## Role

Hermes Architect

## Verdict

APPROVED_ARCHITECTURE_LOCK

## Architecture decision

The next wave is a role-based enforcement layer built on top of the completed Agent PR 1–10 foundation.

The architecture must be implemented in this exact order:

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

## Required role flow

```text
Scope Owner
→ Grill Reviewer
→ Hermes Architect
→ GSD Implementer
→ QA/Safety Reviewer
→ Evidence Recorder
→ Human Approver
```

## Design principle

Roles are not personalities. Roles are enforceable contracts:

```text
allowed_actions
forbidden_actions
allowed_paths
forbidden_paths
required_outputs
handoff_targets
safe_flags
```

## Non-goals until PR 18 is complete

```text
auto-merge
mobile approval screen
agent worker
patch executor
broker action
paper order trigger
live config mutation
runtime behavior change
strategy/ranker work
profitability work
```

## Acceptance gates for this lock

The repo must contain:

```text
docs/agent-governance-role-based-enforcement-wave.md
Grill handoff
Hermes handoff
GSD handoff
clear PR 11–18 sequence
explicit no-deviation rule
explicit safe flags
```

## Safe flags

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
real_order_id=null
```

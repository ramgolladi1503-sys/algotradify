# Agent Governance + Role-Based Mini-Agent Enforcement Wave

## Status

Locked.

This document is the source-of-truth scope for the next agent governance wave after the completed Agent PR 1–10 mini-scope and completed Runtime Correction PR 1–10 wave.

## Hard rule

The next implementation wave is strictly limited to:

```text
Agent Governance PR 11–18 only.
No deviation until completion.
```

Every PR in this wave must pass through the mini-agent architecture. After PR 18 is complete, every future PR must pass through the same architecture by repository enforcement, not by repeated manual prompting.

## Completed baseline

The existing agent mini-scope is complete:

```text
Agent PR 1  — Agent Work Request Contract
Agent PR 2  — Agent Scope Guard
Agent PR 3  — Agent Approval and Evidence Journal
Agent PR 4  — Local Agent Work CLI
Agent PR 5  — Agent Task Store
Agent PR 6  — POST /agent/tasks Intake Webhook
Agent PR 7  — Agent Task Query API
Agent PR 8  — Read-only Dashboard Agent Panel
Agent PR 9  — Patch-only Approval API
Agent PR 10 — Dashboard Patch Approval Controls
```

The next wave does not reopen those PRs. It builds enforcement above them.

## Locked PR order

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

No PR may be skipped. No PR may be replaced by a different feature. No product feature work resumes until this wave is complete unless a severe blocker is explicitly documented and approved.

## Mandatory role-based flow

Every scoped work item must move through this role flow:

```text
Work Request Created
→ Scope Owner validates task boundary
→ Grill reviews risk, fake progress, weak assumptions, and scope drift
→ Hermes defines architecture, contracts, files, acceptance gates, and non-goals
→ GSD implements scoped patch/tests only
→ QA/Safety reviews behavior, unsafe paths, broker/live boundaries, and test strength
→ Evidence Recorder validates proof, tests, handoff artifacts, and acceptance gates
→ Human Approver decides merge-readiness
→ CI enforces the architecture
→ Architecture audit report is generated
```

## Roles

### Scope Owner

Purpose: own the task boundary before any design or implementation.

Allowed:

```text
approve task boundary
reject scope creep
define product/non-product status
define files allowed and files not allowed
```

Forbidden:

```text
write implementation patch
bypass safety review
approve merge without evidence
```

### Grill Reviewer

Purpose: challenge the task before implementation.

Allowed:

```text
critique scope
find fake progress
identify overengineering
identify missing proof
reject weak assumptions
```

Forbidden:

```text
generate implementation patch
approve merge
change runtime/broker/live behavior
```

### Hermes Architect

Purpose: define architecture and contracts.

Allowed:

```text
design architecture
define contracts
map workflow
create acceptance gates
define files to change and files not to touch
```

Forbidden:

```text
write implementation patch
touch broker/live/order paths
approve merge
weaken test requirements
```

### GSD Implementer

Purpose: implement only the approved scoped patch.

Allowed:

```text
generate tests
generate scoped patch
fix scoped test failures
update scoped docs
```

Forbidden:

```text
expand scope
auto-merge
touch forbidden files
touch broker/live/order config without explicit approval
remove safety checks
weaken tests
```

### QA/Safety Reviewer

Purpose: prove the implementation is safe and behaviorally tested.

Allowed:

```text
review tests
review changed-file scope
review safety flags
review broker/live/order boundaries
request changes
```

Forbidden:

```text
write implementation patch as reviewer
approve unsafe behavior
ignore weak shape-only tests
bypass evidence
```

### Evidence Recorder

Purpose: make the proof auditable.

Allowed:

```text
record commands run
record test results
record acceptance proof
record safety boundary
record reject conditions
```

Forbidden:

```text
approve merge alone
hide failed tests
turn missing evidence into pass
```

### Human Approver

Purpose: final merge-readiness decision.

Allowed:

```text
approve merge-readiness after all gates pass
reject merge-readiness when evidence is weak
require explicit exception documentation
```

Forbidden:

```text
bypass safety blockers silently
approve forbidden-path changes without explicit reason
turn role flow failures into pass
```

## Required safe flags

Every role artifact, task record, approval record, validator output, CI gate result, and audit report must preserve these fields where relevant:

```text
read_only=true
is_order_action=false
broker_api_called=false
live_mode_touched=false
allowed_for_live_execution=false
real_order_id=null
```

If a future scoped PR genuinely needs different values, this document must be updated through the same role-based architecture first. Until then, those values are fixed.

## Explicit non-goals until PR 18 is complete

Do not build:

```text
auto-merge
mobile approval screen
agent worker
AI patch executor
agent-created broker action
agent-triggered paper orders
agent-triggered live config
dashboard expansion
unrelated refactor
strategy provider work
ranker work
profitability work
broker adapter work
live execution behavior
```

## PR 11 — Agent Role Registry Contract

Goal: define roles as code, not prompt text.

Expected files:

```text
agent_system/role_registry.py
agent_system/role_contracts.py
tests/test_agent_role_registry.py
docs/agent-role-registry.md
```

Must prove:

```text
Hermes cannot implement patches.
Grill cannot generate code.
GSD cannot touch broker/live paths without approval.
QA/Safety cannot modify implementation as reviewer.
Evidence Recorder cannot approve merge.
Human Approver cannot bypass safety blockers silently.
```

## PR 12 — Role-Based Workflow State Machine

Goal: make role order enforceable.

Expected lifecycle:

```text
REQUESTED
→ SCOPED_BY_SCOPE_OWNER
→ REVIEWED_BY_GRILL
→ DESIGNED_BY_HERMES
→ IMPLEMENTED_BY_GSD
→ REVIEWED_BY_QA_SAFETY
→ EVIDENCE_RECORDED
→ HUMAN_APPROVED
→ MERGE_READY
```

Must block:

```text
REQUESTED → IMPLEMENTED_BY_GSD
DESIGNED_BY_HERMES → MERGE_READY
IMPLEMENTED_BY_GSD → HUMAN_APPROVED without QA/Safety
EVIDENCE_RECORDED without test proof
MERGE_READY with missing handoff artifacts
```

## PR 13 — Role Handoff Artifact Contract

Goal: define what each role must produce.

Required artifacts per scoped PR:

```text
docs/pr-handoffs/<TASK>-scope-owner.md
docs/pr-handoffs/<TASK>-grill.md
docs/pr-handoffs/<TASK>-hermes.md
docs/pr-handoffs/<TASK>-gsd.md
docs/pr-handoffs/<TASK>-qa-safety.md
docs/pr-handoffs/<TASK>-evidence.md
```

Each artifact must include:

```text
role_id
task_id
scope_decision
files_allowed
files_forbidden
risks_found
tests_required
acceptance_gates
verdict
safe_flags
```

## PR 14 — PR Handoff Evidence Validator

Goal: validate role artifacts before merge-readiness.

Expected command:

```bash
python scripts/validate_agent_handoffs.py --task-id <TASK_ID>
```

Must fail if:

```text
Scope Owner handoff missing
Grill handoff missing
Hermes handoff missing
GSD handoff missing
QA/Safety handoff missing
Evidence handoff missing
safe flags missing
handoff verdict invalid
required acceptance gates missing
```

## PR 15 — CI Agent Architecture Gate

Goal: make the architecture unavoidable in GitHub Actions.

Expected file:

```text
.github/workflows/agent-architecture-ci.yml
```

CI must fail if:

```text
role registry invalid
workflow state invalid
handoff artifacts missing
changed files outside approved scope
safe flags broken
agent tests failing
```

## PR 16 — Changed-File Scope Auditor

Goal: compare actual changed files against approved task scope.

Expected files:

```text
agent_system/changed_file_auditor.py
scripts/audit_agent_changed_files.py
tests/test_changed_file_auditor.py
docs/agent-changed-file-scope-auditor.md
```

Must block:

```text
changed file outside allowed_paths
changed file inside forbidden_paths
high-risk path without human approval
broker/live/config/runtime file without explicit approval
```

## PR 17 — PR Template and Local Developer Gate

Goal: catch missing architecture proof before pushing.

Expected files:

```text
.github/pull_request_template.md
scripts/agent_pr_gate.py
tests/test_agent_pr_gate.py
docs/agent-pr-developer-gate.md
```

PR template must require:

```text
task_id
role flow completed
handoff files
changed files
files intentionally not touched
safety boundary
tests run
acceptance proof
reject conditions
```

## PR 18 — Architecture Replay / Audit Report

Goal: generate final merge-readiness proof.

Expected files:

```text
agent_system/architecture_audit.py
scripts/generate_agent_architecture_audit.py
tests/test_agent_architecture_audit.py
docs/agent-architecture-audit-report.md
```

Report must include:

```text
task_id
roles_completed
roles_missing
workflow_state
handoff_status
changed_file_scope_status
test_evidence_status
safety_status
human_approval_status
merge_ready
```

## Final enforced flow after PR 18

After PR 18, every future PR must pass:

```text
Role registry valid
→ workflow state valid
→ handoff artifacts valid
→ changed files inside scope
→ safety flags valid
→ tests passed
→ evidence recorded
→ human approval recorded
→ merge-ready report generated
```

## Rejection rules

Reject any PR in this wave if it:

```text
skips PR order
adds product features
adds runtime worker behavior
adds broker/live/order behavior
adds agent auto-merge
adds mobile approval screen
changes dashboard controls outside explicit scope
weakens existing tests
uses shape-only tests for safety behavior
silently expands files touched
omits role handoff artifacts
omits acceptance proof
```

## Operating instruction

Until PR 18 is merged, the only valid next work is the next PR in the locked PR 11–18 order. After PR 18 is merged, the architecture itself must enforce this discipline for all future work.

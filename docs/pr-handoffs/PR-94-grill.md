# PR 94 — Grill Scope Review

## Role

Grill reviewer only. No product implementation. No code files changed in this stage.

## Proposed PR

PR 94 — Paper Session Boundary and Reset Controls

## Why this PR is next

PR 87 created the canonical paper event journal.
PR 88 created the deterministic paper state reducer.
PR 89 added event ordering and idempotency guard.
PR 90 added deterministic rebuild from journal.
PR 91 added reconciliation between rebuilt and observed state.
PR 92 added a minimal in-memory paper trading pipeline orchestrator.
PR 93 added local JSONL paper evidence persistence.

The next missing control is session boundary discipline. Now that paper evidence can be persisted, the product needs a safe way to mark session start/end and reset boundaries without deleting evidence or mixing old and new runs.

Without PR94, later scenario tests, export bundles, replay datasets, and expectancy validation can be polluted by prior paper evidence.

## Scope decision

Approved with strict limits.

PR94 may add a paper-only session boundary/control layer that creates evidence records representing session lifecycle boundaries. It must not delete evidence, mutate historical records, wire runtime, expose API/UI, call brokers, or place orders.

## Goal

Create a local, paper-only session boundary layer that can:

1. Create deterministic paper session identifiers.
2. Build safe session start records.
3. Build safe session end records.
4. Build safe reset marker records.
5. Validate session boundary records.
6. Optionally persist those records through the PR93 persistence layer.
7. Load/filter session records without mutating history.

Session reset must mean: create a boundary marker for future isolation.

Session reset must not mean: destructive deletion.

## Files allowed to change

Expected files:

```text
paper_trading/session_boundary.py
tests/test_paper_session_boundary.py
docs/paper-session-boundary-reset-controls.md
paper_trading/__init__.py
PROJECT_STATE.md
docs/pr-handoffs/PR-94-gsd.md
docs/pr-handoffs/PR-94-hermes.md
```

Optional only if strongly justified:

```text
scripts/mark_paper_session_boundary.py
```

Recommendation: do not add CLI in PR94 unless implementation stays tiny. The core API and tests are enough.

## Files forbidden to touch

```text
api/
frontend/
broker_contract/
execution_safety/
execution_readiness/
strategies/
movement_engine/
top_selector/
paper_broker/
main.py
runtime wiring
live execution paths
real broker adapters
credential/config files
```

Also forbidden unless a blocking contract bug is proven and separately scoped:

```text
paper_trading/event_journal.py
paper_trading/events.py
paper_trading/state_reducer.py
paper_trading/event_ordering.py
paper_trading/rebuild.py
paper_trading/reconciliation.py
paper_trading/pipeline.py
paper_trading/persistence.py
```

PR94 may import and use persistence write/load functions. It must not mutate persistence behavior.

## Safety boundary

All session boundary results and records must expose:

```text
paper_only=true
read_only=true where applicable
is_order_action=false
broker_api_called=false
real_order_id=null
```

Write operations may write local paper evidence boundary records only. They must still expose:

```text
paper_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

No real broker execution.
No LIVE orders.
No order submit/modify/cancel/exit controls.
No API endpoint.
No UI/dashboard.
No runtime wiring.
No strategy/provider work.
No ML/ranker work.
No credential usage.
No destructive deletion.

## Approved design shape

The builder may add:

```text
PaperSessionBoundaryStatus
PaperSessionBoundaryResult
paper_session_boundary_schema_contract()
build_paper_session_id()
build_paper_session_boundary_record()
mark_paper_session_boundary()
load_paper_session_boundaries()
validate_paper_session_boundary_record()
```

Recommended statuses:

```text
BUILT
MARKED
LOADED
EMPTY
BLOCKED
```

Recommended boundary types:

```text
SESSION_START
SESSION_END
RESET_MARKER
```

Recommended record fields:

```text
schema_version
record_type
session_id
boundary_type
created_at_epoch
reason
metadata
paper_only
read_only
is_order_action
broker_api_called
real_order_id
```

If persisted through PR93, record_type should remain explicit, for example:

```text
PAPER_SESSION_BOUNDARY
```

## Required behavior

1. Build deterministic session IDs from explicit inputs.
2. Require session_id for boundary records unless using builder helper.
3. Require valid boundary_type.
4. Require created_at_epoch or allow explicit None only if documented.
5. Validate reason/metadata safely.
6. Block unsafe metadata flags.
7. Persist boundary records only through PR93 persistence functions if persistence is included.
8. Load boundary records without mutating evidence.
9. Treat missing evidence file as EMPTY.
10. Never delete, truncate, or rewrite existing evidence.
11. Never silently ignore corrupt evidence from persistence.

## What PR94 must not do

Do not add end-to-end scenario suite. That is PR95.
Do not add export bundle. That is PR96.
Do not add replay dataset generation. That starts PR97.
Do not add runtime scheduler integration.
Do not add API/UI/dashboard.
Do not call brokers.
Do not touch live mode.
Do not implement strategy logic.
Do not implement metrics/expectancy logic.
Do not delete or truncate evidence files.

## Failure cases

The session boundary layer must fail closed on:

```text
missing session_id when required
invalid boundary_type
unsafe metadata flags
broker_api_called=true
is_order_action=true
real_order_id present
non-object metadata
missing evidence path when marking boundary
persistence write BLOCKED
persistence load BLOCKED
corrupt evidence from persistence
unknown boundary record shape
attempted destructive reset/delete/truncate flag
```

## Negative tests required

Minimum required tests:

```text
schema contract exposes safe flags and allowed boundary types
build_paper_session_id is deterministic
valid SESSION_START boundary builds safely
valid SESSION_END boundary builds safely
valid RESET_MARKER boundary builds safely
missing session_id blocks boundary build
invalid boundary_type blocks
unsafe metadata order-action flag blocks
broker_api_called metadata blocks
real_order_id metadata blocks
non-object metadata blocks
mark boundary writes through persistence safely
persistence write blocker returns BLOCKED
load missing file returns EMPTY safely
load filters only PAPER_SESSION_BOUNDARY records
boundary result has no submit/modify/cancel/exit/place controls
reset marker does not delete or truncate existing evidence
```

## Acceptance proof required

Focused:

```bash
python -m pytest tests/test_paper_session_boundary.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_evidence_persistence.py tests/test_paper_trading_pipeline.py -q
```

Additional paper truth regression if session layer imports broader contracts:

```bash
python -m pytest tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py -q
```

## Regression risks

1. Reset controls can easily become destructive. Do not delete or truncate evidence.
2. Session logic can accidentally become runtime wiring. Do not wire it anywhere.
3. Boundary metadata can hide unsafe flags if validation is shallow. Validate recursively.
4. Persisting boundaries through PR93 must not mutate PR93 persistence behavior.
5. Future scenario/export/replay work may need richer session indexing, but do not overbuild now.

## Merge blockers

Block merge if any of these happen:

```text
broker/live files touched
API or UI files touched
runtime scheduler/main wiring touched
new strategy/provider/ranker logic added
pipeline/persistence contract changed without separate scope
evidence files deleted/truncated/rewritten
reset operation is destructive
unsafe metadata gets written successfully
corrupt persistence load is silently ignored
safe flags missing from boundary result
PR lacks GSD and Hermes artifacts
```

## Required GSD instruction

Builder must not code until this Grill artifact is accepted.

Builder must create:

```text
docs/pr-handoffs/PR-94-gsd.md
```

The GSD artifact must list implementation choices, actual files changed, tests added, commands, and any deviation from this Grill scope.

## Required Hermes instruction

Reviewer must create after implementation:

```text
docs/pr-handoffs/PR-94-hermes.md
```

Hermes must compare the actual changed files against this Grill scope and explicitly approve, request changes, or reject.

## Final Grill verdict

Approved for a minimal local paper session boundary and reset marker layer only.

Do not implement runtime wiring, destructive reset, export bundle, scenario suite, replay dataset, API, UI/dashboard, broker execution, live execution, new strategies, or ML/ranker work in PR94.

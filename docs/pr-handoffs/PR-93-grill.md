# PR 93 — Grill Scope Review

## Role

Grill reviewer only. No code implementation. No product modules changed in this stage.

## Proposed PR

PR 93 — Paper Evidence Persistence Layer

## Why this PR is next

PR 87 created the canonical paper event journal.
PR 88 created the deterministic paper state reducer.
PR 89 added event ordering and idempotency guard.
PR 90 added deterministic rebuild from journal.
PR 91 added reconciliation between rebuilt and observed state.
PR 92 added a minimal in-memory paper trading pipeline orchestrator.

The next missing step is durable evidence persistence for the paper pipeline output. PR92 proves the pipeline can produce canonical events, stage diagnostics, and derived state in memory. PR93 must persist that evidence safely so later PRs can reset sessions, run scenarios, export bundles, replay data, and validate expectancy.

This PR must not become runtime execution. It must not append real broker orders. It must not add API/UI/dashboard. It must not change strategy logic.

## Scope decision

Approved with strict limits.

PR93 may add a deterministic, file-based paper evidence persistence layer for PR92 pipeline results and related paper evidence. It must be append-safe or write-safe, schema-versioned, paper-only, and testable with temp files.

## Goal

Create a paper-only persistence layer that can safely write and read paper pipeline evidence to local files without broker calls, runtime wiring, API exposure, UI/dashboard, or strategy changes.

The persistence layer must support future replay/export work, but PR93 itself should only persist and load evidence records.

## Files allowed to change

Expected files:

```text
paper_trading/persistence.py
tests/test_paper_evidence_persistence.py
docs/paper-evidence-persistence-layer.md
paper_trading/__init__.py
PROJECT_STATE.md
docs/pr-handoffs/PR-93-gsd.md
docs/pr-handoffs/PR-93-hermes.md
```

Optional only if strongly justified:

```text
scripts/persist_paper_evidence.py
```

Recommendation: do not add CLI in PR93 unless implementation stays tiny. Persistence API plus tests is enough.

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
```

PR93 may import and use pipeline result shapes. It must not mutate the PR92 pipeline contract.

## Safety boundary

The persistence layer must remain:

```text
paper_only=true
read_only=true for load/read operations
is_order_action=false
broker_api_called=false
real_order_id=null
```

Write operations are allowed only for local paper evidence files and must still be:

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

## Approved design shape

The builder may add:

```text
PaperEvidencePersistenceStatus
PaperEvidenceWriteResult
PaperEvidenceReadResult
paper_evidence_persistence_schema_contract()
write_paper_evidence_record()
load_paper_evidence_records()
validate_paper_evidence_record()
```

Recommended statuses:

```text
WRITTEN
LOADED
EMPTY
BLOCKED
```

Recommended persistence format:

```text
JSONL
```

Each record should be one JSON object per line and should include:

```text
schema_version
record_type
record_id
cycle_id
candidate_id
strategy_id
created_at_epoch
source
payload
payload_hash
paper_only
read_only
is_order_action
broker_api_called
real_order_id
```

`payload` may contain the PR92 pipeline result or selected evidence payload.

`payload_hash` should be deterministic and derived from canonical JSON serialization.

## Required behavior

1. Validate record input before writing.
2. Block unsafe flags.
3. Block real_order_id.
4. Block broker_api_called=true.
5. Block is_order_action=true.
6. Require cycle_id and record_type.
7. Require payload object.
8. Write JSONL deterministically.
9. Create parent directory only for the target evidence path, not broad directories.
10. Load records from JSONL.
11. Block corrupt JSONL lines on load.
12. Preserve schema version and safe flags.
13. Avoid silent fallback. Broken evidence must be visible as BLOCKED.

## What PR93 must not do

Do not add session reset controls. That is PR94.
Do not add end-to-end scenario suite. That is PR95.
Do not add export bundle. That is PR96.
Do not add replay dataset generation. That starts PR97.
Do not add API/UI/dashboard.
Do not wire into runtime scheduler.
Do not touch live mode.
Do not call brokers.
Do not implement strategy logic.
Do not implement metrics/expectancy logic.

## Failure cases

The persistence layer must fail closed on:

```text
missing evidence path
invalid evidence path type
missing record_type
missing cycle_id
missing payload
non-object payload
unsafe payload flags
broker_api_called=true
is_order_action=true
real_order_id present
corrupt JSONL line
non-object JSONL record
duplicate record_id if duplicate handling is implemented
payload hash mismatch if hash validation is implemented
```

## Negative tests required

Minimum required tests:

```text
schema contract exposes safe flags and JSONL boundary
valid evidence record writes successfully
written evidence can be loaded back deterministically
missing evidence path blocks
missing cycle_id blocks
missing record_type blocks
missing payload blocks
non-object payload blocks
unsafe order-action payload blocks
broker_api_called payload blocks
real_order_id payload blocks
corrupt JSONL line blocks load
non-object JSONL line blocks load
load missing file returns EMPTY safely
write result has no submit/modify/cancel/exit/place controls
load result has no submit/modify/cancel/exit/place controls
```

If payload_hash is implemented:

```text
payload hash is deterministic
payload hash mismatch blocks load or validation
```

## Acceptance proof required

Focused:

```bash
python -m pytest tests/test_paper_evidence_persistence.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_trading_pipeline.py tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py -q
```

If persistence imports event/reducer contracts, also run:

```bash
python -m pytest tests/test_paper_event_journal.py tests/test_paper_state_reducer.py tests/test_paper_event_ordering.py -q
```

## Regression risks

1. Persistence can accidentally become runtime wiring. Do not wire it anywhere.
2. Evidence file writes can hide bad input if validation is weak. Fail closed.
3. Broad path creation can be dangerous. Keep path handling explicit and test temp-dir only.
4. JSON hashing must be stable if implemented.
5. Future export/replay work may need additional metadata, but do not overbuild now.

## Merge blockers

Block merge if any of these happen:

```text
broker/live files touched
API or UI files touched
runtime scheduler/main wiring touched
new strategy/provider/ranker logic added
pipeline contract changed without separate scope
journal/reducer/rebuild/reconciliation contracts changed
unsafe input gets written successfully
corrupt JSONL silently ignored
load fallback hides broken evidence
safe flags missing from write/read result
PR lacks GSD and Hermes artifacts
```

## Required GSD instruction

Builder must not code until this Grill artifact is accepted.

Builder must create:

```text
docs/pr-handoffs/PR-93-gsd.md
```

The GSD artifact must list implementation choices, actual files changed, tests added, commands, and any deviation from this Grill scope.

## Required Hermes instruction

Reviewer must create after implementation:

```text
docs/pr-handoffs/PR-93-hermes.md
```

Hermes must compare the actual changed files against this Grill scope and explicitly approve, request changes, or reject.

## Final Grill verdict

Approved for a minimal local JSONL Paper Evidence Persistence Layer only.

Do not implement runtime wiring, session reset, export bundle, scenario suite, replay dataset, API, UI/dashboard, broker execution, live execution, new strategies, or ML/ranker work in PR93.

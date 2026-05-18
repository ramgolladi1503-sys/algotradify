# PR 92 — Grill Scope Review

## Role

Grill reviewer only. No code. No commits beyond this scope artifact. No implementation.

## Proposed PR

PR 92 — Paper Trading Pipeline Orchestrator

## Why this PR is next

PR 87 created the canonical paper event journal.
PR 88 created the deterministic paper state reducer.
PR 89 added event ordering and idempotency guard.
PR 90 added deterministic rebuild from journal.
PR 91 added reconciliation between rebuilt and observed state.

The next missing piece is not UI, API, dashboard, strategy, or live trading. The next missing piece is a controlled paper-cycle orchestrator that wires the existing paper modules into one deterministic, report-only pipeline without broker execution.

The orchestrator must prove that the paper pipeline can run in one safe cycle and produce structured evidence from existing components.

## Scope decision

Approved with strict limits.

This PR may orchestrate existing paper-only components. It must not create new trading strategy logic, persistence layer, API, dashboard, runtime wiring, or broker/live behavior.

## Goal

Create a read-only/simulation-only paper pipeline orchestrator that takes controlled inputs and runs one deterministic paper cycle through existing paper modules, producing a structured pipeline result.

The orchestrator should become the backend seam that later PRs can persist, scenario-test, export, and eventually expose through read-only APIs.

## Files allowed to change

Expected files:

```text
paper_trading/pipeline.py
tests/test_paper_trading_pipeline.py
docs/paper-trading-pipeline-orchestrator.md
paper_trading/__init__.py
PROJECT_STATE.md
docs/pr-handoffs/PR-92-gsd.md
docs/pr-handoffs/PR-92-hermes.md
```

Optional only if justified by implementation:

```text
scripts/run_paper_pipeline.py
```

The CLI is optional. Prefer not to add it unless the builder can keep it tiny and read-only.

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

Also forbidden:

```text
paper_trading/event_journal.py
paper_trading/events.py
paper_trading/state_reducer.py
paper_trading/event_ordering.py
paper_trading/rebuild.py
paper_trading/reconciliation.py
```

Those modules are already established contracts. PR92 may import and use them, but must not mutate their behavior unless a blocking integration bug is proven and scoped separately.

## Safety boundary

The orchestrator must remain:

```text
paper_only=true
read_only=true where reporting-only
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
No persistence layer.
No new movement providers.
No ML/ranker work.
No strategy promotion logic.

## Approved design shape

The builder may add:

```text
PaperTradingPipelineStatus
PaperTradingPipelineResult
paper_trading_pipeline_schema_contract()
run_paper_trading_pipeline()
validate_paper_trading_pipeline_inputs()
```

Expected statuses:

```text
COMPLETED
NOOP
BLOCKED
```

The pipeline should be deterministic and explicit. It should accept controlled inputs only, likely:

```text
cycle_id
candidate / candidate_id
strategy_id
intent input
lifecycle input
fill input or quote input
position input / mark input if needed
journal_path optional or in-memory journal option
```

The Grill recommendation is to keep PR92 minimal:

1. Validate input.
2. Build paper intent using existing intent bridge if available.
3. Build lifecycle evidence using existing lifecycle module if available.
4. Simulate fill using existing fill simulation module if available.
5. Convert produced outputs into canonical paper events.
6. Run ordering guard.
7. Reduce state.
8. Rebuild/reconcile only if doing so does not require persistence mutation.
9. Return one structured result with safe flags and diagnostics.

If this becomes too large, cut scope to an in-memory orchestrator only. Persistence belongs to PR93.

## What PR92 must not do

Do not add durable persistence. That is PR93.
Do not add session reset/boundary controls. That is PR94.
Do not add end-to-end scenario suite. That is PR95.
Do not add export bundle. That is PR96.
Do not add replay dataset. That starts PR97.
Do not add API/UI. That starts much later.
Do not call brokers.
Do not wire into runtime scheduler.
Do not touch live mode.

## Failure cases

The orchestrator must fail closed on:

```text
missing cycle_id
missing candidate_id or strategy_id when required
unsafe input flags
invalid intent input
invalid lifecycle transition
stale or missing quote/fill input
fill simulation blocked
canonical event validation failure
ordering guard failure
state reducer blocker
reconciliation blocker if reconciliation is included
any indication of real broker order id
broker_api_called=true
is_order_action=true
paper_only!=true
```

## Negative tests required

Minimum required tests:

```text
schema contract exposes safe flags and scope boundary
valid minimal paper cycle returns COMPLETED
missing required input returns BLOCKED
unsafe order-action input returns BLOCKED
broker_api_called input returns BLOCKED
real_order_id input returns BLOCKED
blocked fill simulation returns BLOCKED
invalid canonical event conversion returns BLOCKED
ordering guard blocker returns BLOCKED
reducer blocker returns BLOCKED
pipeline output has no submit/modify/cancel/exit/place controls
same input produces same pipeline result
pipeline does not mutate existing journal/reducer/rebuild/reconciliation contracts
```

If CLI is added, also require:

```text
CLI exits 0 on COMPLETED/NOOP
CLI exits 2 on BLOCKED
CLI JSON preserves safe flags
```

## Acceptance proof required

Focused:

```bash
python -m pytest tests/test_paper_trading_pipeline.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_event_journal.py tests/test_paper_state_reducer.py tests/test_paper_event_ordering.py tests/test_paper_journal_rebuild.py tests/test_paper_state_reconciliation.py -q
```

If the builder touches intent/lifecycle/fill modules indirectly, also run their tests if present.

## Regression risks

1. The orchestrator can easily become a fake all-in-one architecture layer. Keep it thin.
2. Persistence temptation is high. Do not add persistence in PR92.
3. Runtime wiring temptation is high. Do not wire into runtime.
4. Strategy/provider temptation is high. Do not add new trading logic.
5. Converting module outputs into canonical paper events may expose mismatched schemas. If it is too big, stop and narrow scope rather than patching unrelated modules.

## Merge blockers

Block merge if any of these happen:

```text
broker/live files touched
API or UI files touched
runtime scheduler/main wiring touched
new strategy/provider/ranker logic added
persistent storage added beyond optional local test temp files
journal/reducer/rebuild/reconciliation contracts changed without separate scope
unsafe input succeeds
tests only assert object shape
pipeline silently skips failed stages
result hides blockers or drift
safe flags missing from result
PR lacks GSD and Hermes artifacts
```

## Required GSD instruction

Builder must not code until this Grill artifact is accepted.

Builder must create:

```text
docs/pr-handoffs/PR-92-gsd.md
```

The GSD artifact must list the exact implementation choices and actual files changed.

## Required Hermes instruction

Reviewer must create after implementation:

```text
docs/pr-handoffs/PR-92-hermes.md
```

Hermes must compare actual changed files against this Grill scope and explicitly approve, request changes, or reject.

## Final Grill verdict

Approved for a minimal in-memory Paper Trading Pipeline Orchestrator only.

Do not implement persistence, API, UI, dashboard, runtime wiring, broker execution, live execution, new strategies, or ML/ranker work in PR92.

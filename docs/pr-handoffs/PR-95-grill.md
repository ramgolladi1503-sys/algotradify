# PR 95 — Grill Scope Review

## Role

Grill reviewer only. No product implementation. No code files changed in this stage.

## Proposed PR

PR 95 — End-to-End Paper Scenario Suite

## Why this PR is next

PR 87 created the canonical paper event journal.
PR 88 created the deterministic paper state reducer.
PR 89 added event ordering and idempotency guard.
PR 90 added deterministic rebuild from journal.
PR 91 added reconciliation between rebuilt and observed state.
PR 92 added a minimal in-memory paper trading pipeline orchestrator.
PR 93 added local JSONL paper evidence persistence.
PR 94 added non-destructive paper session boundaries and reset markers.

The next missing step is proving these layers work together across complete controlled paper scenarios. We need scenario-level evidence before export bundles, replay datasets, expectancy validation, dashboards, broker readiness, or live work.

PR95 must test the paper system end-to-end using deterministic inputs, local temp files, and existing paper-only modules. It must not become runtime trading, strategy expansion, API/UI, or export/replay work.

## Scope decision

Approved with strict limits.

PR95 may add an end-to-end paper scenario suite and small scenario helper layer if needed. The suite should run controlled scenarios across pipeline, persistence, session boundary, rebuild, and reconciliation where appropriate.

## Goal

Create deterministic end-to-end paper scenarios that prove the paper evidence chain works from session start through paper pipeline output, evidence persistence, session boundary markers, evidence reload, derived state, and reconciliation checks.

The suite should expose scenario results, blockers, warnings, safe flags, and acceptance proof.

## Files allowed to change

Expected files:

```text
paper_trading/scenarios.py
tests/test_paper_scenarios.py
docs/paper-scenario-suite.md
paper_trading/__init__.py
PROJECT_STATE.md
docs/pr-handoffs/PR-95-gsd.md
docs/pr-handoffs/PR-95-hermes.md
```

Optional only if strongly justified:

```text
fixtures/paper_scenarios/*.json
```

Recommendation: start with in-test scenario fixtures/helpers first. Add fixture files only if they improve clarity and remain deterministic.

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
paper_trading/session_boundary.py
```

PR95 may import and use these modules. It must not mutate their contracts.

## Safety boundary

All scenario results must expose:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

Scenarios may write only to local temp evidence files in tests.

No real broker execution.
No LIVE orders.
No order submit/modify/cancel/exit controls.
No API endpoint.
No UI/dashboard.
No runtime wiring.
No strategy/provider work.
No ML/ranker work.
No credential usage.
No destructive reset behavior.
No export bundle.
No replay dataset generation.

## Approved design shape

The builder may add:

```text
PaperScenarioStatus
PaperScenarioResult
paper_scenario_schema_contract()
run_paper_scenario()
run_standard_paper_scenarios()
validate_paper_scenario_inputs()
```

Recommended statuses:

```text
PASSED
FAILED
BLOCKED
```

Recommended scenario names:

```text
FULL_FILL_HAPPY_PATH
PARTIAL_FILL_PATH
NO_FILL_PATH
STALE_QUOTE_BLOCKED_PATH
SESSION_RESET_MARKER_PATH
```

Do not overbuild a generic scenario framework. Keep it simple and deterministic.

## Required behavior

A scenario should be able to:

1. Create or accept a deterministic session id.
2. Mark SESSION_START through PR94 session boundary controls.
3. Run PR92 paper pipeline with controlled inputs.
4. Persist PR92 pipeline evidence through PR93 persistence.
5. Optionally mark SESSION_END or RESET_MARKER depending on scenario.
6. Load persisted evidence.
7. Validate safe flags.
8. Validate expected scenario status/outcome.
9. Report scenario PASS/FAIL/BLOCKED with blockers/warnings.

Where useful, scenario validation may inspect pipeline state and events directly. Do not force journal rebuild if the scenario is not using the canonical journal file. Rebuild/reconciliation checks may be included only when they remain simple and use existing modules without mutation.

## What PR95 must not do

Do not add export bundle. That is PR96.
Do not add replay dataset generation. That starts PR97.
Do not add expectancy validation or profitability scoring.
Do not add runtime scheduler integration.
Do not add API/UI/dashboard.
Do not call brokers.
Do not touch live mode.
Do not implement strategy logic.
Do not add new movement providers.
Do not add ML/ranker work.
Do not make scenarios depend on real market data.

## Failure cases

The scenario suite must fail closed or fail visibly on:

```text
missing scenario name
invalid scenario input
unsafe scenario payload flags
pipeline BLOCKED unexpectedly
persistence write BLOCKED
persistence load BLOCKED
session boundary BLOCKED
expected outcome mismatch
real_order_id present anywhere
broker_api_called=true anywhere
is_order_action=true anywhere
missing persisted evidence
unexpected evidence count
corrupt evidence file
```

## Negative tests required

Minimum required tests:

```text
schema contract exposes safe flags and scenario names
full fill scenario passes deterministically
partial fill scenario passes deterministically
no fill scenario passes deterministically
stale quote scenario reports BLOCKED or expected failure safely
session reset marker scenario appends marker without altering previous evidence
missing scenario name blocks
unknown scenario name blocks
unsafe scenario input blocks
pipeline blocker is surfaced
persistence blocker is surfaced
session boundary blocker is surfaced
corrupt evidence load is surfaced
scenario result has no submit/modify/cancel/exit/place controls
same scenario input produces same result
scenario suite does not mutate established paper contracts
```

## Acceptance proof required

Focused:

```bash
python -m pytest tests/test_paper_scenarios.py -q
```

Adjacent regression:

```bash
python -m pytest tests/test_paper_session_boundary.py tests/test_paper_evidence_persistence.py tests/test_paper_trading_pipeline.py -q
```

Additional paper truth regression if scenario code imports broader contracts:

```bash
python -m pytest tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py tests/test_paper_event_ordering.py tests/test_paper_state_reducer.py -q
```

## Regression risks

1. Scenario code can become a fake runtime runner. Keep it test/helper-only and deterministic.
2. Scenario fixtures can become brittle if they mirror implementation internals too closely.
3. Scenario suite can grow into strategy work. Do not add new strategy logic.
4. Evidence counts may become fragile; assert meaningful outcomes, not every incidental field.
5. Rebuild/reconciliation should not be forced if the scenario is not journal-backed.

## Merge blockers

Block merge if any of these happen:

```text
broker/live files touched
API or UI files touched
runtime scheduler/main wiring touched
new strategy/provider/ranker logic added
export bundle added
replay dataset generated
profitability/expectancy scoring added
scenario uses real broker or live market data
unsafe scenario input succeeds
scenario failure is silently treated as pass
established pipeline/persistence/session contracts changed without separate scope
PR lacks GSD and Hermes artifacts
```

## Required GSD instruction

Builder must not code until this Grill artifact is accepted.

Builder must create:

```text
docs/pr-handoffs/PR-95-gsd.md
```

The GSD artifact must list implementation choices, actual files changed, tests added, commands, and any deviation from this Grill scope.

## Required Hermes instruction

Reviewer must create after implementation:

```text
docs/pr-handoffs/PR-95-hermes.md
```

Hermes must compare the actual changed files against this Grill scope and explicitly approve, request changes, or reject.

## Final Grill verdict

Approved for a deterministic paper-only end-to-end scenario suite.

Do not implement export bundle, replay dataset, expectancy/profitability validation, runtime wiring, API, UI/dashboard, broker execution, live execution, new strategies, or ML/ranker work in PR95.

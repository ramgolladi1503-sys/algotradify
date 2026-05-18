# PR 95 — Hermes Diff Review and State Handoff

## Role

Reviewer/state recorder only. Review final diff against Grill scope. Do not implement product code.

## Grill artifact reviewed

Path: docs/pr-handoffs/PR-95-grill.md

## GSD artifact reviewed

Path: docs/pr-handoffs/PR-95-gsd.md

## Final changed files

- paper_trading/scenarios.py
- tests/test_paper_scenarios.py
- docs/paper-scenario-suite.md
- paper_trading/__init__.py
- PROJECT_STATE.md
- docs/pr-handoffs/PR-95-grill.md
- docs/pr-handoffs/PR-95-gsd.md
- docs/pr-handoffs/PR-95-hermes.md

## Changed files match approved scope

Yes.

## Forbidden files touched

No.

Forbidden layers not touched:

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

## Safety boundary preserved

Yes.

The implementation is deterministic paper scenario evidence only. It does not add export bundles, replay datasets, expectancy scoring, runtime wiring, API/UI, broker/live behavior, or strategy/ranker work.

## Behavior tests added

Yes.

Tests cover full fill, partial fill, no fill, expected stale quote block, session reset marker path, standard suite execution, deterministic repeatability, and upstream contract references.

## Negative tests added

Yes.

Tests cover missing scenario name, unknown scenario name, unsafe scenario overrides, pipeline blocker surfacing, persistence blocker surfacing, session boundary blocker surfacing, corrupt evidence surfacing, and forbidden order-control text.

## Focused test command

```bash
python -m pytest tests/test_paper_scenarios.py -q
```

## Adjacent regression command

```bash
python -m pytest tests/test_paper_session_boundary.py tests/test_paper_evidence_persistence.py tests/test_paper_trading_pipeline.py -q
```

Additional paper truth regression:

```bash
python -m pytest tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py tests/test_paper_event_ordering.py tests/test_paper_state_reducer.py -q
```

## CI status

Pending.

## Remaining risks

- Scenario helpers are intentionally simple and deterministic. They are not a runtime runner.
- Scenario evidence currently validates pipeline/persistence/session interactions, not profitability.
- Export and replay are intentionally absent and should remain PR96+ work.

## Reject before merge if

- Runtime wiring appears.
- API/UI/dashboard work appears.
- Broker/live execution appears.
- Strategy/ranker work appears.
- Export bundle or replay dataset generation appears.
- Expectancy/profitability scoring appears.
- Scenario failures are silently treated as pass.
- Stage-gate workflow fails due to missing handoff evidence.

## State update after merge

Latest merged PR: GitHub PR TBD / Product PR 95 — End-to-End Paper Scenario Suite
Product PR: PR 95
Next PR only: PR 96 — Paper Evidence Export Bundle
What not to touch next: broker/live/API/UI/dashboard/strategy/ML unless explicitly scoped by roadmap.

## Hermes verdict

Approve, pending CI.

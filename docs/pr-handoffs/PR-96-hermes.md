# PR 96 — Hermes Diff Review and State Handoff

## Role

Reviewer/state recorder only. Review final diff against Grill scope. Do not implement product code.

## Grill artifact reviewed

Path: docs/pr-handoffs/PR-96-grill.md

## GSD artifact reviewed

Path: docs/pr-handoffs/PR-96-gsd.md

## Final changed files

- paper_trading/export_bundle.py
- tests/test_paper_export_bundle.py
- docs/paper-evidence-export-bundle.md
- paper_trading/__init__.py
- PROJECT_STATE.md
- docs/pr-handoffs/PR-96-grill.md
- docs/pr-handoffs/PR-96-gsd.md
- docs/pr-handoffs/PR-96-hermes.md

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

The implementation is local paper evidence export only. It does not add replay dataset generation, expectancy/profitability validation, runtime wiring, API/UI, broker/live behavior, strategy/ranker work, cloud upload, or dashboard/report layer.

## Behavior tests added

Yes.

Tests cover valid bundle build, manifest creation, checksum creation, bundle validation, deterministic output, manifest loading, and stable file hashing.

## Negative tests added

Yes.

Tests cover missing bundle root, missing evidence path, corrupt evidence, unsafe evidence, unsafe scenario result, checksum mismatch, missing manifest, missing evidence file, forbidden replay dataset output, forbidden expectancy/profitability fields, and forbidden order-control text.

## Focused test command

```bash
python -m pytest tests/test_paper_export_bundle.py -q
```

## Adjacent regression command

```bash
python -m pytest tests/test_paper_scenarios.py tests/test_paper_evidence_persistence.py tests/test_paper_session_boundary.py -q
```

Additional paper truth regression:

```bash
python -m pytest tests/test_paper_trading_pipeline.py tests/test_paper_state_reconciliation.py tests/test_paper_journal_rebuild.py -q
```

## CI status

Pending.

## Remaining risks

- The bundle is a local folder structure, not an archive or upload mechanism.
- Replay dataset generation is intentionally absent and belongs to PR97.
- Export manifest determinism depends on explicit created_at_epoch when callers need stable bundle ids.

## Reject before merge if

- Runtime wiring appears.
- API/UI/dashboard work appears.
- Broker/live execution appears.
- Strategy/ranker work appears.
- Replay dataset generation appears.
- Expectancy/profitability scoring appears.
- Unsafe evidence is exported successfully.
- Checksum mismatch is ignored.
- Stage-gate workflow fails due to missing handoff evidence.

## State update after merge

Latest merged PR: GitHub PR TBD / Product PR 96 — Paper Evidence Export Bundle
Product PR: PR 96
Next PR only: PR 97 — Paper Replay Dataset Builder
What not to touch next: broker/live/API/UI/dashboard/strategy/ML unless explicitly scoped by roadmap.

## Hermes verdict

Approve, pending CI.

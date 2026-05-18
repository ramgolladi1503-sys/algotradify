# Runtime Correction PR 1 — Grill Review

## Scope under review

Runtime Correction PR 1 — Runtime Ownership Audit.

This PR must add only a read-only audit script, tests, documentation, project-state update, and handoff artifacts.

## Hard challenge

The risk is scope drift. The audit must not become the migration.

If this PR imports Tradebot source, changes `main.py`, changes runtime resolution, adds auth endpoints, edits the Control Tower, or changes broker behavior, it is already wrong.

## Why this PR is necessary

The project currently needs a hard truth checkpoint before moving code. Without this audit, the next PRs could keep building around a runtime boundary that is still ambiguous.

## Required proof

The PR must prove both states through tests:

1. Wrapper/external-compatible posture is detected and marked unsafe for normal feature continuation.
2. Native posture is detected only when root `main.py`, root `core/`, root `config/`, and no external fallback markers are present.

## Required safety flags

Audit output must include:

```json
{
  "read_only": true,
  "audit_only": true,
  "is_order_action": false,
  "broker_api_called": false,
  "real_order_id": null,
  "live_mode_touched": false
}
```

## Rejection conditions

Reject this PR if any of the following occur:

- runtime behavior changes
- `main.py` is modified
- `runtime_contract.py` is modified
- Tradebot source is imported
- API/frontend/paper/agent code is modified
- broker auth or broker calls are introduced
- tests are weak shape-only checks without behavior fixtures
- audit output hides blockers behind warnings

## Grill verdict

Approved only as an audit-only first correction step.

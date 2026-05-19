# Runtime Correction PR 2 — Grill Review

## Scope under review

Runtime Correction PR 2 — Tradebot Source Import Manifest and Collision Report.

This PR must plan the import only. It must not copy Tradebot source, replace `main.py`, change runtime behavior, or touch protected algotradify product layers.

## Hard challenge

The risk is pretending a plan is the import. The planner must be explicit that `source_imported=false` and `runtime_behavior_changed=false`.

The second risk is hiding collisions. If `main.py` or scripts collide, the planner must report them as unresolved decisions, not auto-resolve them.

## Why this PR is necessary

A native source import can damage existing algotradify work if done blindly. The repo already has API, frontend, paper, replay, safety, movement, and agent layers that must be protected.

## Required proof

The PR must prove:

1. missing source is blocked
2. missing required Tradebot markers are blocked
3. clean source candidates are reported without copying
4. root `main.py` collision is deferred to PR 5
5. script collisions require curated decisions
6. protected target prefixes are documented
7. unresolved decisions force `safe_to_import=false`
8. output contains non-executing safe flags

## Rejection conditions

Reject this PR if any of these happen:

- Tradebot source is copied
- `main.py` is changed
- `runtime_contract.py` is changed
- API/frontend/paper/agent code is changed
- planner mutates the target repo
- collisions are silently allowed
- secrets/runtime/log patterns are missing from exclusions
- safe flags are missing

## Grill verdict

Approved only as a planning/collision-report PR.

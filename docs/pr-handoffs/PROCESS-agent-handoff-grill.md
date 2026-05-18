# Process PR — Grill Scope Review

## Role

Grill reviewer only. No product code. No runtime changes.

## Proposed PR

Process PR — Add independent stage handoff protocol.

## Why this PR is next

The previous stage-gate process forced PR-body evidence, but it did not force separate artifacts for Grill, GSD, and Hermes roles. The user wants visible independent-stage workflow, not one silent ChatGPT pass pretending to do all roles.

## Scope decision

Approved.

## Files allowed to change

- docs/agent-handoff-protocol.md
- docs/pr-handoffs/TEMPLATE-grill.md
- docs/pr-handoffs/TEMPLATE-gsd.md
- docs/pr-handoffs/TEMPLATE-hermes.md
- docs/pr-handoffs/PROCESS-agent-handoff-grill.md
- docs/pr-handoffs/PROCESS-agent-handoff-gsd.md
- docs/pr-handoffs/PROCESS-agent-handoff-hermes.md
- scripts/check_pr_stage_gates.py
- .github/pull_request_template.md

## Files forbidden to touch

- paper_trading product modules
- broker/live execution code
- api
- frontend/dashboard
- runtime wiring
- strategies
- movement_engine
- ranker/ML code

## Safety boundary

Process-only. No trading runtime behavior changes.

## Failure cases

- PR body lacks handoff artifact references.
- PR body claims independence without artifacts.
- Checker allows missing Grill/GSD/Hermes evidence.
- Process PR touches runtime/product files.

## Negative tests required

- Missing required handoff phrases must fail the PR body checker.
- Missing required stage sections must fail the PR body checker.

## Acceptance proof required

- PR template includes handoff artifact references and independence declarations.
- Checker requires those references and declarations.
- This PR itself includes Grill, GSD, and Hermes handoff artifacts.

## Regression risks

- Future PRs with older body format will fail until updated.
- The checker is text-level; it enforces evidence presence, not true semantic independence.

## Merge blockers

- Any runtime/product code change.
- Any broker/LIVE/API/UI/strategy change.
- Checker not requiring all three artifact references.
- PR body not using the new handoff evidence section.

## Final Grill verdict

Approved for process-only implementation.

# Algotradify Agent Operating Contract

This repository is a trading-system safety project. Treat every agent-assisted change as production-risk work, even when the change is paper-only or documentation-only.

The goal is not to create more PRs. The goal is to create fewer, stronger PRs that improve stability, safety, paper/live readiness, or profitability validation.

## Non-negotiable rules

- Never work directly on `main`.
- Never use broker credentials in agent sessions.
- Never place real orders from tests, scripts, docs examples, or agent workflows.
- Never introduce LIVE behavior unless the PR explicitly scopes LIVE behavior and proves readiness gates.
- Never let SIM or PAPER paths call real broker placement APIs.
- Never hide broken data with silent fallback.
- Never add dashboard/UI work unless the PR explicitly requires it.
- Never do unrelated cleanup, renaming, formatting, or architecture polish.
- Never add weak tests that only assert object shape.
- Every PR must include acceptance proof.
- Every non-trivial PR must include pre-code scope review evidence and post-code review evidence.

## Mandatory stage gates

Every non-trivial PR must pass these gates in order.

### Gate 1 — Pre-code scope review

Purpose: kill ambiguity before implementation starts.

The agent must output and the PR must preserve:

1. Exact PR title and goal.
2. Why this PR is next.
3. Files allowed to change.
4. Files forbidden to touch.
5. Safety boundary.
6. Failure cases and negative tests.
7. Acceptance proof.
8. Regression risks.
9. Merge blockers.

If this gate is vague, do not code.

### Gate 2 — Scoped implementation

Purpose: implement one approved scope only.

Execution rules:

- One PR scope only.
- One branch only.
- No opportunistic refactors.
- No extra abstractions unless required by the scoped behavior.
- No broker imports in read-only, paper-only, or test-only layers.
- Preserve backward-compatible evidence and log schemas unless the scope explicitly changes them.
- Add focused tests plus adjacent regression tests where relevant.

### Gate 3 — Post-code PR review

Purpose: review the actual diff before merge.

The agent must compare the final diff against the approved scope and answer:

1. Did the changed files match the approved scope?
2. Did any forbidden file or layer change?
3. Did tests prove behavior, not just shape?
4. Did unsafe inputs fail closed?
5. Did any broker, LIVE, API, UI, runtime, strategy, or ML/ranker work sneak in?
6. Are safety flags preserved where relevant?
7. What can still break?
8. What should be rejected before merge?

If this gate finds scope creep, request changes before merge.

### Gate 4 — State recording

After each PR is merged or rejected, update project state in the next appropriate PR or provide the exact state update.

Record:

- Latest merged Product PR and GitHub PR.
- Files changed.
- Tests added.
- Commands that passed.
- Commands that failed.
- Risks left behind.
- What must not be touched next.
- The next PR only.

Hermes or any long-memory project agent may maintain this state, but it must not decide trades, handle secrets, place orders, or bypass safety gates.

## Required implementation output

Before changing code, the agent must provide:

```text
Proposed design:
Files to change:
Files not to touch:
Safety boundary:
Negative tests:
Acceptance proof:
Regression risks:
Merge blockers:
```

After changing code, the agent must provide:

```text
Patch summary:
Tests added:
Focused test command:
Adjacent regression command:
Safety proof:
Scope compliance check:
What was intentionally not touched:
Self-review:
```

## Safety fields that must stay explicit

Paper/read-only layers must keep these flags visible where relevant:

```text
paper_only=true
read_only=true
is_order_action=false
broker_api_called=false
real_order_id=null
```

Any PR that removes, weakens, or hides these fields must explain why and add strict tests. Default answer: reject the PR.

## Merge blockers

Block merge if any of these are true:

- The PR changes unrelated files.
- The PR body lacks pre-code scope review evidence.
- The PR body lacks post-code review evidence.
- Tests prove only object shape, not failure behavior.
- Unsafe input falls through as success.
- A fallback silently replaces broken data.
- A paper/read-only path imports or calls broker placement.
- A LIVE path is touched without explicit safety flags and tests.
- The PR description lacks test commands and acceptance proof.
- The PR creates dashboard/UI work outside scope.
- The PR adds strategy/provider/ML/ranker work before the current paper-truth foundation is complete.

## Current operating posture

Default posture until explicitly changed:

```text
mode=paper_truth_foundation
live_execution=false
broker_order_placement=false
dashboard_changes=false
strategy_provider_expansion=false
ml_ranker_work=false
```

## Correct use of agents

Use agents in this order:

```text
Grill / pre-code scope review
    ↓
approved PR decision scope
    ↓
GSD / coding agent executes one phase
    ↓
tests and acceptance proof
    ↓
post-code PR review against actual diff
    ↓
Hermes / project memory records state after merge
```

## Forbidden agent usage

Do not use agents for:

- live trading decisions
- broker credential handling
- order placement
- bypassing safety gates
- broad refactors
- strategy expansion before paper truth is proven
- dashboard work before the roadmap allows it
- ML/ranker work before expectancy is proven

## Brutal rule

The product is not helped by more moving parts. It is helped by stricter truth, stronger tests, and smaller verified changes.
